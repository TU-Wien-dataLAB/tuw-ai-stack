import os
import pprint
import random
from locust import HttpUser, LoadTestShape, constant, events, task, between

import locust.stats
import requests
import json


locust.stats.CSV_STATS_INTERVAL_SEC = 2  # default is 1 second

STORY_TOPICS = [
    "a fantasy adventure about a magical forest",
    "a sci-fi tale about time travel to the year 2150",
    "a mystery story involving an ancient artifact",
    "a romance story set in a coastal village",
    "a horror story about a haunted house",
]

SUMMARY_TOPICS = [
    "Quantum mechanics",
    "Mona Lisa",
    "Python (programming language)",
    "Great Wall of China",
    "Albert Einstein",
    "Black hole",
    "French Revolution",
    "Mars",
    "Artificial intelligence",
    "William Shakespeare",
]


def get_wikipedia_content(topics, max_characters=5_000):
    cache_file = os.path.join(os.path.dirname(__file__), "export", "cache.json")
    articles = {}

    # Load existing cache if it exists
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            cache = json.load(f)
    else:
        cache = {}

    base_url = "https://en.wikipedia.org/w/api.php"

    for topic in topics:
        if topic in cache:
            # Use cached content if available
            articles[topic] = cache[topic]
        else:
            # Fetch content if not in cache
            params = {
                "action": "query",
                "format": "json",
                "prop": "extracts",
                "explaintext": True,
                "titles": topic,
            }
            response = requests.get(base_url, params=params)

            if response.status_code == 200:
                data = response.json()
                pages = data.get("query", {}).get("pages", {})
                page = next(iter(pages.values()))
                content = page.get("extract", "No content available.")[:max_characters]
                articles[topic] = content
                # Update cache with new content
                cache[topic] = content
            else:
                raise RuntimeError()

    # Save updated cache to file
    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=4)

    return articles


SUMMARY_DATA = get_wikipedia_content(SUMMARY_TOPICS)
pprint.pprint({k: len(v) for k, v in SUMMARY_DATA.items()})


class ChatUser(HttpUser):
    wait_time = between(10, 30)  # Time between requests from the same user
    # wait_time = constant(0)
    abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = None

    def get_story_payload(self, topic: str):
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": f"Write a short story about {topic}."},
            ],
            "temperature": 0.6,
        }

    def get_summary_payload(self, text: str):
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant."},
                {
                    "role": "user",
                    "content": f"Summarize this Wikipedia article:\n{text}",
                },
            ],
            "temperature": 0.6,
        }

    @property
    def headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('LITE_LLM_API_KEY')}",
        }

    @task
    def story(self):
        # Randomly select a topic
        topic = random.choice(STORY_TOPICS)

        # Make a POST request to the completions endpoint
        response = self.client.post(
            "chat/completions",
            json=self.get_story_payload(topic),
            headers=self.headers,
            name=self.model,
        )

    @task
    def summary(self):
        topic = random.choice(SUMMARY_TOPICS)
        text = SUMMARY_DATA[topic]

        # Make a POST request to the completions endpoint
        response = self.client.post(
            "chat/completions",
            json=self.get_summary_payload(text),
            headers=self.headers,
            name=self.model,
        )


class Qwen32B(ChatUser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = "qwen-32b"


class QwenCoder32B(ChatUser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = "qwen-coder-32b"


class QwenCoder3B(ChatUser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = "qwen-coder-3b"


class DeepSeekR132B(ChatUser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = "deepseek-r1-32b"


class Pixtral12B(ChatUser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = "pixtral-12b"

    def _payload(self, input: str):
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "You are a helpful AI assistant.",
                        },
                        {
                            "type": "text",
                            "text": input,
                        },
                    ],
                }
            ],
            "temperature": 0.6,
        }

    def get_story_payload(self, topic: str):
        return self._payload(f"Write a short story about {topic}.")

    def get_summary_payload(self, text: str):
        return self._payload(f"Summarize this Wikipedia article:\n{text}")


class ModelStepShape(LoadTestShape):
    use_common_options = True

    def tick(self):
        num_classes = len(self.runner.user_classes)
        run_time = self.get_run_time()
        max_users = self.runner.environment.parsed_options.users * num_classes
        spawn_rate = self.runner.environment.parsed_options.spawn_rate * num_classes

        # Calculate the theoretical user count based on spawn rate
        theoretical_user_count = int(run_time * spawn_rate)

        # Round the theoretical user count to the nearest multiple of num_classes
        user_count = (theoretical_user_count // num_classes) * num_classes

        # Ensure the user count does not exceed the maximum number of users
        user_count = min(user_count, max_users)
        print(self.runner.user_classes_count)

        return (user_count, spawn_rate)
