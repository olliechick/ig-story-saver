#!/usr/bin/python3

import codecs
import os
import urllib.request
from datetime import datetime
import sentry_sdk

import piexif
import requests
from instabot import Bot
from mega import Mega
from pytz import timezone

LOGIN_FILE_PATH = "login_details.txt"
SETTINGS_FILE_PATH = "settings.txt"
USERNAMES_FILE_PATH = "usernames.txt"
STORIES_DIR = "stories"
MEGA_SEP = "/"
DATETIME_FORMAT = '%Y_%m_%d %I.%M%p'

TIMESTAMP = 'timestamp'
URL = 'url'

ENV_MEGA_EMAIL = 'MEGA_EMAIL'
ENV_MEGA_PASSWORD = 'MEGA_PASSWORD'
ENV_IG_USERNAME = 'IG_USERNAME'
ENV_IG_PASSWORD = 'IG_PASSWORD'
ENV_USERNAMES_URL = 'USERNAMES_URL'
ENV_TIMEZONE_NAME = 'TIMEZONE_NAME'
ENV_SENTRY_DSN = 'SENTRY_DSN'


def to_json(python_object):
    if isinstance(python_object, bytes):
        return {'__class__': 'bytes',
                '__value__': codecs.encode(python_object, 'base64').decode()}
    raise TypeError(repr(python_object) + ' is not JSON serializable')


def from_json(json_object):
    if '__class__' in json_object and json_object['__class__'] == 'bytes':
        return codecs.decode(json_object['__value__'].encode(), 'base64')
    return json_object


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
    tz = os.environ[ENV_TIMEZONE_NAME] if ENV_TIMEZONE_NAME in os.environ else None
    return datetime.fromtimestamp(timestamp, timezone(tz)).strftime(DATETIME_FORMAT) \
        .replace('_', '-').replace("AM", "am").replace("PM", "pm").replace(" 0", " ")


def get_extension_from_url(url):
    return url.split('?')[0].split('.')[-1]


def get_stories(usernames):
    items_key = 'items'
    taken_at_key = 'taken_at'
    video_versions_key = 'video_versions'
    image_versions_key = 'image_versions2'
    candidates_key = 'candidates'
    url_key = 'url'

    # api = login()
    bot = Bot()
    bot.login(username=os.environ[ENV_IG_USERNAME], password=os.environ[ENV_IG_PASSWORD])

    stories = dict()

    for username in usernames:
        print("Getting stories for " + username)
        user_id = bot.get_user_id_from_username(username)
        raw_stories = bot.get_user_reel(user_id)[items_key]

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


def upload_files_to_mega(folders_and_filenames):
    mega = Mega()
    email = os.environ[ENV_MEGA_EMAIL]
    password = os.environ[ENV_MEGA_PASSWORD]
    m = mega.login(email, password)

    for folder_name, filename in folders_and_filenames:
        possible_folders = m.find(folder_name, exclude_deleted=True)
        if possible_folders is None:
            full_folder_name = STORIES_DIR + MEGA_SEP + folder_name
            print("Creating folder: " + full_folder_name)
            m.create_folder(full_folder_name)
            possible_folders = m.find(folder_name, exclude_deleted=True)
        m.upload(filename, possible_folders[0])
        print("Uploading " + filename)


def get_username_list():
    request = requests.get(os.environ[ENV_USERNAMES_URL])
    return [username.strip() for username in request.text.splitlines()]


def main():
    if ENV_SENTRY_DSN in os.environ:
        sentry_sdk.init(os.environ[ENV_SENTRY_DSN])

    usernames = get_username_list()
    print("Usernames: " + ', '.join(usernames))

    setup_env()

    print("Getting stories...")
    stories = get_stories(usernames)
    print(stories)
    print("Downloading stories...")
    usernames_and_filenames = download_stories(stories)
    print("Uploading stories...")
    upload_files_to_mega(usernames_and_filenames)


if __name__ == '__main__':
    main()
