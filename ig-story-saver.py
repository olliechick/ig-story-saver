#!/usr/bin/python3

import codecs
import json
import os
import urllib.request
from datetime import datetime

import piexif
from instagram_private_api import Client, ClientCookieExpiredError, ClientLoginRequiredError, ClientLoginError, \
    ClientError
from mega import Mega

from file_io import read_file

LOGIN_FILE_PATH = "login_details.txt"
SETTINGS_FILE_PATH = "settings.txt"
USERNAMES_FILE_PATH = "usernames.txt"
STORIES_DIR = "stories"
MEGA_SEP = "/"

TIMESTAMP = 'timestamp'
URL = 'url'

ENV_MEGA_EMAIL = 'MEGA_EMAIL'
ENV_MEGA_PASSWORD = 'MEGA_PASSWORD'


def to_json(python_object):
    if isinstance(python_object, bytes):
        return {'__class__': 'bytes',
                '__value__': codecs.encode(python_object, 'base64').decode()}
    raise TypeError(repr(python_object) + ' is not JSON serializable')


def from_json(json_object):
    if '__class__' in json_object and json_object['__class__'] == 'bytes':
        return codecs.decode(json_object['__value__'].encode(), 'base64')
    return json_object


def on_login_callback(api, new_settings_file):
    cache_settings = api.settings
    with open(new_settings_file, 'w') as outfile:
        json.dump(cache_settings, outfile, default=to_json)
        print('SAVED: {0!s}'.format(new_settings_file))


def login():
    """ Logs in using details in login_details.txt """
    settings_file_path = SETTINGS_FILE_PATH
    username, password = read_file(LOGIN_FILE_PATH)[:2]
    username = username.strip()
    password = password.strip()
    device_id = None
    api = None

    try:
        settings_file = settings_file_path
        if not os.path.isfile(settings_file):
            # settings file does not exist
            print('Unable to find file: {0!s}'.format(settings_file))

            # login new
            api = Client(username, password, on_login=lambda x: on_login_callback(x, settings_file_path))
        else:
            with open(settings_file) as file_data:
                cached_settings = json.load(file_data, object_hook=from_json)
            print('Reusing settings: {0!s}'.format(settings_file))

            device_id = cached_settings.get('device_id')
            # reuse auth settings
            api = Client(username, password, settings=cached_settings)

    except (ClientCookieExpiredError, ClientLoginRequiredError) as e:
        print('ClientCookieExpiredError/ClientLoginRequiredError: {0!s}'.format(e))

        # Login expired
        # Do relogin but use default ua, keys and such
        api = Client(username, password, device_id=device_id,
                     on_login=lambda x: on_login_callback(x, settings_file_path))

    except ClientLoginError as e:
        print('ClientLoginError {0!s}'.format(e))
        exit(9)
    except ClientError as e:
        print('ClientError {0!s} (Code: {1:d}, Response: {2!s})'.format(e.msg, e.code, e.error_response))
        exit(9)
    except Exception as e:
        print('Unexpected Exception: {0!s}'.format(e))
        exit(99)

    return api


def set_date(filename, timestamp):
    """ Sets date of file `filename` to the time in the POSIX timestamp `timestamp`. """
    extension = filename.split('.')[-1]
    if extension == "jpg":
        exif_dict = piexif.load(filename)
        time = datetime.fromtimestamp(timestamp)
        exif_dict['Exif'] = {piexif.ExifIFD.DateTimeOriginal: time.strftime("%Y:%m:%d %H:%M:%S")}
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, filename)

    os.utime(filename, (timestamp, timestamp))


def format_datetime(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y_%m_%d %I.%M%p') \
        .replace('_', '-').replace("AM", "am").replace("PM", "pm").replace(" 0", " ")


def get_extension_from_url(url):
    return url.split('?')[0].split('.')[-1]


def get_stories(usernames):
    user_key = 'user'
    pk_key = 'pk'
    reel_key = 'reel'
    items_key = 'items'
    taken_at_key = 'taken_at'
    video_versions_key = 'video_versions'
    image_versions_key = 'image_versions2'
    candidates_key = 'candidates'
    url_key = 'url'

    api = login()

    stories = dict()

    for username in usernames:
        user_info = api.username_info(username)
        user_id = user_info[user_key][pk_key]
        feed = api.user_story_feed(user_id)
        raw_stories = feed[reel_key][items_key]

        stories_for_this_user = []

        for story in raw_stories:
            timestamp = story[taken_at_key]
            if video_versions_key in story:
                url = story[video_versions_key][0][url_key]
            elif image_versions_key in story:
                url = story[image_versions_key][candidates_key][0][url_key]
            else:
                raise Exception("No image or video versions")
            stories_for_this_user.append({TIMESTAMP: timestamp, URL: url})

        stories[username] = stories_for_this_user

    return stories


def setup_env():
    if not os.path.exists(STORIES_DIR):
        os.mkdir(STORIES_DIR)


def download_stories(stories):
    usernames_and_filenames = []
    for username, user_stories in stories.items():
        if not os.path.exists(os.path.join(STORIES_DIR, username)):
            os.mkdir(os.path.join(STORIES_DIR, username))
        for story in user_stories:
            timestamp = story[TIMESTAMP]
            url = story[URL]

            original_filename = format_datetime(timestamp)
            fully_specified_filename = os.path.join(STORIES_DIR, username,
                                                    original_filename + '.' + get_extension_from_url(url))

            i = 1
            while os.path.exists(fully_specified_filename):
                filename = f"{original_filename} ({i})"
                fully_specified_filename = os.path.join(STORIES_DIR, username,
                                                        filename + '.' + get_extension_from_url(url))
                i += 1

            usernames_and_filenames.append((username, fully_specified_filename))

            urllib.request.urlretrieve(url, fully_specified_filename)
            set_date(fully_specified_filename, timestamp)

    return usernames_and_filenames


def upload_files_to_mega(folders, folders_and_filenames):
    mega = Mega()
    email = os.environ[ENV_MEGA_EMAIL]
    password = os.environ[ENV_MEGA_PASSWORD]
    m = mega.login(email, password)

    for folder_name in folders:
        if m.find(folder_name) is None:
            print("Creating folder: " + folder_name)
            m.create_folder(STORIES_DIR + MEGA_SEP + folder_name)

    for folder_name, filename in folders_and_filenames:
        possible_folders = m.find(folder_name)
        m.upload(filename, possible_folders[0])
        print("Uploading " + filename)


def main():
    usernames = [username.strip() for username in read_file(USERNAMES_FILE_PATH)]
    print("Usernames: " + ', '.join(usernames))

    setup_env()

    print("Getting stories...")
    stories = get_stories(usernames)
    print("Downloading stories...")
    usernames_and_filenames = download_stories(stories)
    print("Uploading stories...")
    upload_files_to_mega(usernames, usernames_and_filenames)


if __name__ == '__main__':
    main()
