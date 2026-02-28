import os

from custom_json_provider import CustomJsonProvider
from data.users import lookup_user
from endpoints import (
    do_follow,
    do_unfollow,
    get_bloom,
    hashtag,
    home_timeline,
    login,
    other_profile,
    register,
    self_profile,
    send_bloom,
    suggested_follows,
    user_blooms,
)

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager


def main():
    load_dotenv()

    app = Flask("PurpleForest")

    app.json = CustomJsonProvider(app)

    # Configure CORS to handle preflight requests
    CORS(
        app,
        supports_credentials=True,
        resources={
            r"/*": {
                "origins": "*",
                "allow_headers": ["Content-Type", "Authorization"],
                "methods": ["GET", "POST", "OPTIONS"],
            }
        },
    )

    app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET_KEY"]
    jwt = JWTManager(app)
    jwt.user_lookup_loader(lookup_user)

    app.add_url_rule("/register", methods=["POST"], view_func=register)
    app.add_url_rule("/login", methods=["POST"], view_func=login)

    app.add_url_rule("/home", view_func=home_timeline)

    app.add_url_rule("/profile", view_func=self_profile)
    app.add_url_rule("/profile/<profile_username>", view_func=other_profile)
    app.add_url_rule("/follow", methods=["POST"], view_func=do_follow)
    app.add_url_rule("/unfollow/<unfollow_username>", methods=["POST"], view_func=do_unfollow)
    app.add_url_rule("/suggested-follows/<limit_str>", view_func=suggested_follows)

    app.add_url_rule("/bloom", methods=["POST"], view_func=send_bloom)
    app.add_url_rule("/bloom/<id_str>", methods=["GET"], view_func=get_bloom)
    app.add_url_rule("/blooms/<profile_username>", view_func=user_blooms)
    app.add_url_rule("/hashtag/<hashtag>", view_func=hashtag)

    app.run(host="0.0.0.0", port="3000", debug=True)


if __name__ == "__main__":
    main()
