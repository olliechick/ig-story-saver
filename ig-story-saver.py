#!/usr/bin/python3

import codecs
import json
import os

from instagram_private_api import Client, ClientCookieExpiredError, ClientLoginRequiredError, ClientLoginError, \
    ClientError

from file_io import open_file

LOGIN_FILE_PATH = "login_details.txt"
SETTINGS_FILE_PATH = "settings.txt"


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
    username, password = open_file(LOGIN_FILE_PATH)[:2]
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


def get_stories(username):
    user_key = 'user'
    full_name_key = 'full_name'

    api = login()

    items_key = 'items'
    pk_key = 'pk'

    user_info = api.username_info(username)
    user_id = user_info[user_key][pk_key]
    feed = api.user_story_feed(user_id)(user_id)
    stories = feed[items_key]

    full_name = stories[0][user_key][full_name_key]
    print(f"Getting stories for {full_name}...")

    print(stories)

    return stories


def main():
    username = input("Download stories from which user? @")

    stories = get_stories(username)
    # download_stories(stories, username)
    # upload_stories(stories)


if __name__ == '__main__':
    main()
