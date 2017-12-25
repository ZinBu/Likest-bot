# coding: utf-8
""" Перпективный бот для заработки лайков на Likest """
# TODO: дополнить функции лимитами от бана(привязка ко времени и количеству сделанного)
# TODO: чтение аккаунтов из файла, автоматический логин по учетным данным
import random
import threading
from time import sleep

import requests
import vk  # external lib
from vkapi import VK


class WorkerVK:
    """ Класс для работы по части ВК """

    def __init__(self):
        self.vk = VK(self.log_in_vk())  # экзэмляр с токеном для работы с методами

    def log_in_vk(self):
        """ Читает токен из файла, иначе - создает по учетным данным. Вовзращает токен """

        scope = "friends,photos,audio,video,docs,notes,pages,status,wall,groups,messages,notifications,offline"
        app_id = 5377227

        try:
            with open("Token", "r") as memory:
                token = memory.read()

        except Exception as error:
            print("Нет токена ВК", error)
            while True:
                log = input("Login: ")
                password = input("Password: ")
                try:
                    session = vk.AuthSession(app_id=app_id, user_login=log,
                                             user_password=password, scope=scope)
                except Exception as error:
                    print("Не авторизироваться в ВК", error)
                else:
                    token = session.get_access_token()
                    with open("Token", "w") as memory:
                        memory.write(token)
                    break
        return token

    def get_user_id(self, user_id=None):
        """  Получение ID пользователя из ВК """

        if user_id:
            id_ = self.vk.api("users.get", user_ids=user_id)["response"][0]
        else:
            id_ = self.vk.api("users.get")["response"][0]["id"]
        return id_

    def set_status(self, status_text):
        """ Установка статуса в вк """

        self.vk.api("status.set", text=status_text)

    def make_repost(self, wall):
        """ Репост себе на стену """

        response = self.vk.api('wall.repost', object=wall)
        if response['success'] == 1:
            return True
        else:
            print("Ошибка при выполнении репоста", response)
            return

    def make_like_from_link(self, link):
        """ Лайк стены или фото по ссылке """

        if "wall" in link:
            identification = link[18:].split('_')  # идентификаторы owner_id и item_id
            try:
                make_like = self.vk.api("likes.add", owner_id=identification[0], item_id=identification[1],
                                        type='post')  # ставим лайк на записи
            except Exception as e:
                print(e)
        else:
            identification = link[19:].split('_')  # идентификаторы owner_id и item_id
            try:
                make_like = self.vk.api("likes.add", owner_id=identification[0], item_id=identification[1],
                                        type='photo')  # ставим лайк на фото
            except Exception as e:
                print(e)
        try:
            if make_like["response"]['likes']:
                return True
        except Exception:
            print("Ошибка при выполнении лайка", make_like)
            return

    def make_comment(self, object_place, message, id_):
        """ Делает комметарий к указанной записи на стене, фото или обсуждении """

        if object_place == "wall":
            try:
                self.vk.api("wall.createComment", owner_id=id_[0], post_id=id_[1], message=message)
                return True
            except Exception as error:
                print("Ошибка в комментировании стены", error)
                return

        elif object_place == "board":
            try:
                self.vk.api("board.createComment", group_id=id_[0], topic_id=id_[1], message=message)
                return True
            except Exception as error:
                print("Ошибка в комментировании обсуждения", error)
                return

        elif object_place == "photos":
            try:
                self.vk.api("photos.createComment", owner_id=id_[0], photo_id=id_[1], message=message)
                return True
            except Exception as error:
                print("Ошибка в комментировании фотографии", error)
                return

    def make_poll(self, poll_owner, poll_id, poll_answer):
        """ Голосуем в опросе """

        try:
            response = self.vk.api("polls.addVote", owner_id=poll_owner, poll_id=poll_id, answer_id=poll_answer)
            if response["response"] == 1:
                return True
        except Exception as error:
            print("Ошибка при голосовании", error)
            return

    def make_friend(self, user_id):
        """ Добавляем друга """

        try:
            response = self.vk.api("friends.add", user_id=user_id)
            if response["response"] == 1:
                return True
        except Exception as error:
            print("Ошибка при добавлении в друзья", error, user_id)
            return

    def group_entrance(self, group_link):
        """ Вступаем в группу """

        try:
            response = self.vk.api("groups.join", group_id=group_link)
            if response["response"] == 1:
                return True
        except Exception as error:
            print("Ошибка при вступлении в группу", error, group_link)
            return

class WorkerLikest:
    """ Класс по работе с likest """

    def __init__(self):
        self.session_likest = requests.Session()  # создание сессии

    def likest_auth(self, vk_id):
        """ Авторизация на лайкисте через лайк ВК"""
        # todo: разделить метод на две части и убрать экзэмляр мб??
        # получение статус-задания на лайкесте для установки в ВК
        vk_status = self.session_likest.post(
            'https://likest.ru/api/users.login?authname=id{0}&validation=status'.format(str(vk_id))).json()
        WorkerVK().set_status(vk_status['status_status'])  # установка статуса
        # отправка на проверку на лайкист и возвращение токена и т.д.
        access = self.session_likest.post(
            'https://likest.ru/api/users.login?authname=id{0}&status_id={1}'.format(str(vk_id),
                                                                                    str(vk_status['status_id']))).json()
        return access

    def get_balance(self):
        """ Узнать баланс на Likest """

        response = self.session_likest.post('https://likest.ru/api/balance.get').json()['balance']
        return response

    def get_coupons(self):
        """ Узнать о купонах созданных купонах """

        response = self.session_likest.post("https://likest.ru/api/coupons.list?list=all").json()['coupons']
        return response

    def create_coupon(self, user_token, amount=1000):
        """ Создание купона. По умолчанию на 1к лайков """

        req = self.session_likest.post(
            "https://likest.ru/api/coupons.create?user_token={0}&count=1&amount={1}".format(str(user_token),
                                                                                            str(amount))).json()
        print(req)
        with open("Coupon_{0}_{1}.txt".format(amount, req["coupons"]), "w") as f:
            f.write(req["coupons"])
            print(req["coupons"])

    def get_object_list_reposts(self):
        """ Получение заданий на репосты. Возвращает список заданий """

        req = self.session_likest.post('https://likest.ru/api/orders.get?type=reposts').json()
        if req['status'] == 'SUCCESS':
            object_list = req['orders']
            print("get_object_list_reposts: ", object_list)  # временный
            return object_list
        else:
            return

    def accept_object_repost(self, repost_object):
        """ Взять задание на выполнение репоста. Возвращает ссылку """

        req = self.session_likest.post('https://likest.ru/api/orders.accept?oid=' + str(repost_object)).json()
        if req['status'] == 'SUCCESS':
            wall = req['link'][14:]
            return wall
        else:
            print("Likest repost: На лайкисте пусто")
            return

    def get_object_list_groups(self):
        """ Получение заданий на группы. Возвращает список заданий """

        req = self.session_likest.post('https://likest.ru/api/orders.getGroups').json()
        if req['status'] == 'SUCCESS':
            object_list = req['orders']
            # print("get_object_list_groups: ", object_list)  # временный
            return object_list
        else:
            return

    def accept_object_groups(self, repost_object):
        """ Взять задание на выполнение репоста. Возвращает ссылку """

        req = self.session_likest.post('https://likest.ru/api/orders.accept?oid=' + str(repost_object)).json()
        if req['status'] == 'SUCCESS':
            link = req['link'].split("/")[-1][4:]
            # print(req)
            # print(link)
            return link
        else:
            print("Likest groups: На лайкисте пусто")
            return

    def get_object_like(self):
        """ Получение задания на лайк. Возвращает ссылку """

        req = self.session_likest.post('https://likest.ru/api/orders.get?type=likes').json()
        if req['status'] == 'ERR_NO_ORDERS':
            # print("Нет заданий по лайкам")
            return
        else:
            return req["link"]

    def get_object_comment(self):
        """ Получение задания на комментарий.
        Возвращает ссылку на страницу с записью
        Расположение объекта накрутки
        Ожидаемый комментраий
        ID владельца записи и ее самой соответственно
        """

        req = self.session_likest.post('https://likest.ru/api/orders.getComments').json()
        if req['status'] == 'ERR_NO_ORDERS':
            # print("Нет заданий по комментированию")
            return
        else:
            return req["link"], req["object_place"], req["message"], req["id"]

    def get_object_poll(self):
        """ Получение задания на голосование.
        Возвращает ссылку на страницу с записью
        Расположение объекта накрутки
        Ожидаемый комментраий
        ID владельца записи и ее самой соответственно
        """

        req = self.session_likest.post('https://likest.ru/api/orders.getPolls').json()
        if req['status'] == 'ERR_NO_ORDERS':
            # print("Нет заданий по голосованию")
            return
        else:
            return req["link"], req["poll_owner"], req["poll_id"], req["poll_answer"]

    def get_object_list_friends(self):
        """ Получение заданий на добавления в друзья. Возвращает список заданий """

        req = self.session_likest.post('https://likest.ru/api/orders.getFriends').json()
        if req['status'] == 'SUCCESS':
            object_list = req['orders']
            return object_list
        else:
            return

    def accept_object_friends(self, friend_object):
        """ Взять задание на добавление друзей. Возвращает ссылку """

        req = self.session_likest.post('https://likest.ru/api/orders.accept?oid=' + str(friend_object)).json()
        if req['status'] == 'SUCCESS':
            try:
                link = req['link'].split("/")[-1][2:]  # получить id из ссылки
                return link
            except Exception as error:
                print(error, req)
        else:
            print("Likest friends: На лайкисте пусто")
            return


class Main:
    """ Основная часть """

    def __init__(self):
        # на этом этапе создаются экзэмпляры с сессией запросов и
        # токеном вк после авторизации или чтения из файла
        self.likest = WorkerLikest()
        self.vk = WorkerVK()
        self.token_likest = self.auth_likest()  # токен пользователя на лайкисте
        print("Авторизации на сервисах прошли успешно")
        sleep(1)
        self.vk.set_status("")  # убираем статус

    def thread(self):
        """ Запуск метода в потоке """

        def run(*args, **kwargs):
            target = threading.Thread(target=self, args=args, kwargs=kwargs)
            target.setDaemon(True)
            target.start()
            return target

        return run

    def auth_likest(self):
        """ Попытка авторизации на лайкисте до состояния успеха """

        while True:
            try:
                vk_id = self.vk.get_user_id()  # получаем id пользователя
                auth_likest = self.likest.likest_auth(vk_id)  # авторизация на лайкисте через установку статуса
                if auth_likest['status'] == 'SUCCESS':
                    print('Вход в лайкист: успешно')
                    token_likest = auth_likest['user_token']  # токен для создания купонов
                    break
            except Exception as error:
                print("Проблемы с входом на лайкист", error)
                sleep(30)
        return token_likest

    @thread
    def balance_and_coupons(self, amount=500):
        """ Проверка баланса, если есть 500 или amount - создаем купон """

        # вывод баланса
        balance = self.likest.get_balance()
        print("Баланс", balance)
        if balance > amount:
            self.likest.create_coupon(self.token_likest, amount)

        sleep(1)
        # информация о созданных купонах
        created_coupons = self.likest.get_coupons()
        print("Созданные купоны: ", created_coupons)

    @thread
    def do_likes(self):
        """ Выполнение лайков. Относительно безопасно """

        day_limit = 450  # дневной лимит 500
        timeout = random.randint(5, 13)  # генерируем случайную задержку от 2 до 5 сек

        print("Начинаем выполнение заданий на лайки...")
        likes_count = 1
        while True:
            # # каждые 50 сделанных лайков проверяем баланс
            # if likes_count % 50 == 0:
            #     self.balance_and_coupons()
            #     sleep(30)  # пауза

            # контроль лимита
            if likes_count == day_limit:
                print("Дневной лимит лайков достигнут!!!")
                break

            obj = self.likest.get_object_like()  # получение ссылки задания на лайк
            # если ссыллка не пустая - ставим лайк
            if obj:
                like = self.vk.make_like_from_link(obj)  # ставим лайк
                if like is True:
                    print("Задание на лайк выполнено: ", likes_count, obj)
                    likes_count += 1
                    sleep(timeout)  # пауза между лайками
                else:
                    # если ссылка получена с лайкиста, но лайк не сделан
                    sleep(timeout)  # пауза
            else:
                print("Задания на лайки кончились. Подождем...")
                sleep(60 * 20)

    @thread
    def do_reposts(self):
        """ Выполнение заданий на репост из списка доступных """

        day_limit = 40  # дневной лимит 50
        timeout = random.randint(40, 90)  # генерируем случайную задержку от 40 до 90 сек

        object_list = self.likest.get_object_list_reposts()
        if object_list:
            # print("Количество заданий: ", len(object_list))
            print("object_list: ", object_list)
            reposts_count = 1
            # выполнение репостов по списку
            for obj in object_list:
                # контроль лимита
                if reposts_count == day_limit:
                    print("Дневной лимит репостов достигнут!!!")
                    break

                try:
                    obj = obj['oid']
                    wall = self.likest.accept_object_repost(obj)  # взятие задания на репост
                    if wall:
                        repost_status = self.vk.make_repost(wall)  # делаем репост
                        if repost_status:
                            print("Репост выполнен: ", reposts_count, obj)
                            reposts_count += 1
                        else:
                            print("Репост не сделан")
                except Exception as error:
                    print(error)
                sleep(timeout)  # пауза между репостами
        else:
            print("Похоже все задания на репосты кончились")

    @thread
    def do_groups(self):
        """ Выполнение заданий на репост из списка доступных """

        day_limit = 25  # дневной лимит 40
        timeout = random.randint(180, 720)  # генерируем случайную задержку

        object_list = self.likest.get_object_list_groups()
        if object_list:
            # print("Количество заданий: ", len(object_list))
            # print("object_list: ", object_list)
            group_count = 1
            # выполнение репостов по списку
            for obj in object_list:
                # контроль лимита
                if group_count == day_limit:
                    print("Дневной лимит вступлений в группы достигнут!!!")
                    break

                try:
                    print('Reward group: ', obj['reward'])
                    uid = obj['oid']
                    group = self.likest.accept_object_groups(uid)  # взятие задания на паблик
                    if group:
                        enter_status = self.vk.group_entrance(group)  # вступаем в паблик
                        if enter_status:
                            print("Вход в паблик выполнен: ", group_count, uid, obj['reward'])
                            group_count += 1
                        else:
                            print("Вход в паблик не сделан", uid)
                except Exception as error:
                    print(error)
                sleep(timeout)  # пауза между репостами
        else:
            print("Похоже все задания на паблики кончились")

    @thread
    def do_comments(self):
        """ Выполнение заданий по комментированию записей. Относительно безопасно """

        day_limit = 75  # дневной лимит 100
        timeout = random.randint(40, 90)  # генерируем случайную задержку от 40 до 90 сек

        print("Начинаем выполнение заданий с комментированием...")
        comments_count = 1
        while True:
            # контроль лимита
            if comments_count == day_limit:
                print("Дневной лимит комментов достигнут!!!")
                break

            obj = self.likest.get_object_comment()  # получение ссылки задания на коммент
            # если ссыллка не пустая - комментим
            if obj:
                comment = self.vk.make_comment(obj[1], obj[2], obj[3])  # делаем коммент
                if comment is True:
                    print("комментарий оставлен: ", comments_count, obj)
                    comments_count += 1
                    sleep(timeout)  # пауза между лайками
                else:
                    # если ссылка получена с лайкиста, но коммент не сделан
                    sleep(timeout)  # пауза
            else:
                print("Задания на комменты кончились. Ждем...")
                sleep(60 * 45)

    @thread
    def do_polls(self):
        """ Выполнение заданий на голосование. Относительно безопасно """

        timeout = random.randint(30, 50)  # генерируем случайную задержку

        print("Начинаем выполнение заданий с голосованием...")
        polls_count = 1
        while True:
            obj = self.likest.get_object_poll()  # получение ссылки на голосование
            # если ссыллка не пустая, делаем задание
            if obj:
                poll = self.vk.make_poll(obj[1], obj[2], obj[3])  # делаем коммент
                if poll is True:
                    print("Задание по голосованию выполнено: ", polls_count, obj)
                    polls_count += 1
                    sleep(timeout)  # пауза между лайками
                else:
                    # если ссылка получена с лайкиста, но голос не сделан
                    sleep(timeout)  # пауза
            else:
                print("Задания по голосованию кончились. Ждем...")
                sleep(60 * 45)

    @thread
    def do_friends(self):
        """ Выполнение заданий на добавления в друзья из списка доступных """

        day_limit = 30  # дневной лимит 50
        timeout = random.randint(40, 90)  # генерируем случайную задержку от 40 до 90 сек

        object_list = self.likest.get_object_list_friends()
        if object_list:
            # print("Количество заданий: ", len(object_list))
            friends_count = 1
            # выполнение репостов по списку
            for obj in object_list:
                # контроль лимита
                if friends_count == day_limit:
                    print("Дневной лимит друзей достигнут!!!")
                    break
                try:
                    uid = obj['oid']
                    friend_link = self.likest.accept_object_friends(uid)  # взятие задания
                    if friend_link:
                        friend_add_status = self.vk.make_friend(friend_link)  # добавляем друга
                        if friend_add_status:
                            print("Друг добавлен: ", friends_count, obj)
                            friends_count += 1
                        else:
                            print("Друг не добавлен", obj, uid)
                except Exception as error:
                    print(error)
                sleep(timeout)  # пауза между репостами
        else:
            print("Похоже все задания на друзей кончились")


if __name__ == '__main__':
    earner = Main()
    earner.do_likes()
    sleep(2)
    earner.do_comments()
    sleep(2)
    earner.do_polls()
    sleep(2)
    earner.do_friends()
    sleep(2)
    earner.do_groups()
    while True:
        earner.balance_and_coupons()
        sleep(60*3)
