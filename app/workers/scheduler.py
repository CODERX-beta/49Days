import time
from dataclasses import dataclass

from app.platforms.instagram_handler import InstagramHandler


@dataclass
class FakePublication:
    id: int
    title: str
    media_url: str


class Scheduler:

    def __init__(self):
        self.instagram = InstagramHandler()

    def run(self):

        print("🚀 Scheduler Started")

        while True:

            publication = FakePublication(
                id=1,
                title="Morning Motivation",
                media_url="https://storage.49days.ai/videos/demo.mp4",
            )

            print("\nFound queued publication.")

            result = self.instagram.publish(publication)

            if result["success"]:
                print(
                    f"Publication marked as POSTED ({result['platform_post_id']})"
                )

            print("\nSleeping for 10 seconds...\n")

            time.sleep(10)


if __name__ == "__main__":
    Scheduler().run()