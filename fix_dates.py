#!/usr/bin/python3
import datetime
import os
import sys

from ig_story_saver import STORIES_DIR, set_date, DATETIME_FORMAT

stories_dir = STORIES_DIR

if len(sys.argv) > 1:
    print("Fixing stories in " + sys.argv[1])
    stories_dir = sys.argv[1]

directories = os.listdir(stories_dir)

for directory in directories:
    for filename in os.listdir(os.path.join(stories_dir, directory)):
        date_string = filename
        if '(' in date_string:
            parts = date_string.split(' ')
            date_string = f'{parts[0]} {parts[1]}'
        else:
            parts = date_string.split('.')
            date_string = f'{parts[0]}.{parts[1]}'

        if len(date_string) == 17:
            date_string = f'{date_string[:11]}0{date_string[11:]}'

        date_string = date_string.replace('-', '_').replace("am", "AM").replace("pm", "PM")
        timestamp = datetime.datetime.strptime(date_string, DATETIME_FORMAT).timestamp()

        set_date(os.path.join(stories_dir, directory, filename), timestamp)
