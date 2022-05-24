# xbot-matcher

A stable pair matching algorithm for [Discord Xbot](https://github.com/Wolemercy/discord-xbot).

This project was developed to get first-hand experience of how AWS Lambda works and by necessary consequence; AWS VPCs and NAT Gateways. It was also required as a feature to achieve the full functionalities of [Discord Xbot](https://github.com/Wolemercy/discord-xbot) and the implementation of the algorithm is tailored to that goal.

## Getting Started

Deploy the project to AWS Lambda and ensure you have the necessary env variables defined (an env template file has been provided). If you're having issues with `psycopg2`, check out [awslambda-psycopg2](https://github.com/jkehler/awslambda-psycopg2). A deployed instance of [Discord Xbot](https://github.com/Wolemercy/discord-xbot) should also be running.

The project can also be run locally if you have a local instance of [Discord Xbot](https://github.com/Wolemercy/discord-xbot);

- Ensure you have the necessary env variables defined. An env template file has been provided.
- Run `python -m venv venv --prompt xbot_venv` to create a virtual environment
- Run `.\venv\Scripts\activate` to activate the virtual environment
- Run `pip install -r requirements.txt` to install relevant dependencies
- Run `python xbot_matching.py` and provide the `guild_id` to create new matches.
