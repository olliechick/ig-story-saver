# IG Story Saver
Saves Instagram stories from a list of users to Mega, a cloud file hosting service.

## Instructions

### Setup

Install packages from `requirements.txt`.

Host a text file on a website with a list of all the usernames whose stories you want to save. For example:

```csv
user1
user2
user3
```

Create the following environment variables:

| Environment variable | Description        | Example    |
|----------------------|--------------------|------------|
| `MEGA_EMAIL`         | Mega email         | `me@example.com` |
| `MEGA_PASSWORD`      | Mega password      | `password`       |
| `IG_USERNAME`        | Instagram username | `username` |
| `IG_PASSWORD`        | Instagram password | `password` |
| `USERNAMES_URL`      | URL of usernames text file | `https://olliechick.co.nz/example.txt` |

### Running

When run, the program will download all the users' stories to a `stories` directory. Each user's stories will be downloaded to a folder named their username, and a file named the time the story was posted, for example: `stories/user1/2020-07-15 9.43am.png`. These will then be uploaded to Mega, using the same directory structure.

Instagram may block the login attempt if, for example, you have a new account or you run it from a server hosted in another country to the one that you normally logged in to your account on. The API this runs on recommends you not use your own account. I recommend creating a burner account and using that (although this won't work for saving stories of users with a private account).