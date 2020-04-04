# Quiz bot

This is a quiz bot for [vk](https://vk.com/) and [telegram](https://telegram.org/) platforms.  
Look how it works:  

![](https://raw.githubusercontent.com/nicko858/quiz-bot/gifs/telegram_demo.gif)

![](https://raw.githubusercontent.com/nicko858/quiz-bot/gifs/vk_demo.gif)

## Prerequisites

### Telegram instructions

- Create telegram-bot using [bot-father](https://telegram.me/BotFather) and remember it's token
- Create telegram-chat(group) and add bot to chat-members
- Get your chat-id using [this manual](https://stackoverflow.com/a/32572159)

### Redis instructions

- Create account on [redislabs](https://app.redislabs.com/), or use existing if you have
- Create database and get it *host*, *port* , *password*

### VK instructions

- Create new [vk-group](https://vk.com/groups?tab=admin)
- Create group token in section `Работа с API` with the following permissions:
  - *управление сообществом*
  - *сообщения сообщества*
- Enable messages send in `Сообщения` - section
- Enable bot features:  
  `Управление` --> `Сообщения` --> `Настройки для бота` and enable `Возможности ботов`
  
## How to deploy local

Python3 should be already installed.

```bash
    git clone https://github.com/nicko858/quiz-bot
    cd quiz-bot
    pip install -r requirements.txt
```

- Create file `.env` in the script directory

- Edit your `.env` - file:

  ```bash
     TELEGRAM_BOT_TOKEN=<your bot token>
     LOGGER_CHAT_ID=<your chat id>
     DB_HOST=<redis database host>
     DB_PORT=<redis database port>
     DB_PASSWD=<redis database password>
     VK_TOKEN=<your vk-group token>
  ```

## How to run local

At first, you need a quiz source file for your bot with the following content as example:

```txt
    Вопрос 1:
    С одним советским туристом в Марселе произошел такой случай. Спустившись
    из своего номера на первый этаж, он вспомнил, что забыл закрутить кран в
    ванной. Когда он поднялся, вода уже затопила комнату. Он вызвал
    горничную, та попросила его обождать внизу. В страхе он ожидал расплаты
    за свою оплошность. Но администрация его не ругала, а, напротив,
    извинилась сама перед ним. За что?

    Ответ:
    За то, что не объяснила ему правила пользования кранами.


    Вопрос 2:
    В своем первоначально узком значении это слово произошло от французского
    глагола, означающего "бить". Сейчас же оно может означать любое
    объединение в систему нескольких однотипных элементов. Назовите это
    слово.

    Ответ:
    Батарея (от battre).
```

Please note that:  

- 1 line break between sections `Вопрос*` and `Ответ`
- 2 line break between both `Вопрос*` and `Ответ` sections
- File have to be in `KOI8-R` - encoding

For demo purposes, you'll find `demo_quiz_source.txt` in this repo. So, you may use it for testing.

Now we are ready to start our bots:

```bash
    nohup python3 vk_quiz_bot.py ./demo_quiz_source.txt &
    nohup python3 telegram_quiz_bot.py ./demo_quiz_source.txt &
```

To stop bots:

```bash
    ps -fe | grep vk_quiz_bot.py
    ps -fe | grep telegram_quiz_bot.py
    kill -9 <vk_quiz_bot PID>
    kill -9 <telegram_quiz_bot PID>
```

## How to deploy on heroku

- Fork current repository
- Make sure, that you have `Procfile` in the repo root and it has this inside:

  ```bash
    bot-quiz-tg: python3 telegram_quiz_bot.py ./demo_quiz_source.txt
    bot-quiz-vk: python3 vk_quiz_bot.py ./demo_quiz_source.txt  
  ```

- Create account on [heroku](https://id.heroku.com) or use existing
- Create new app and connect your github-account
- After successfull github connection, go to `deploy section`
- Choose `Manual deploy` and click `Deploy Branch`(by default -from master)
- After successfull deploy, go to `Settings` and create environment variables in `Config Vars` section:

  ```bash
     TELEGRAM_BOT_TOKEN: <your bot token>
     LOGGER_CHAT_ID: <your chat id>
     DB_HOST: <redis database host>
     DB_PORT: <redis database port>
     DB_PASSWD: <redis database password>
     VK_TOKEN: <your vk-group token>
  ```

- Go to `Resources` and make sure that you have this in `Free Dynos` - section:

    ```bash
    bot-quiz-tg: python3 telegram_quiz_bot.py ./demo_quiz_source.txt
    bot-quiz-vk: python3 vk_quiz_bot.py ./demo_quiz_source.txt
    ```

- Run bots by clicking pencil-icon

## Project Goals

The code is written for educational purposes on online-course for web-developers [dvmn.org](https://dvmn.org/).
