import requests
import os
import json
from ws4py.client.threadedclient import WebSocketBaseClient
from ws4py.manager import WebSocketManager
import time


class Stockfighter():
    base_url = 'https://api.stockfighter.io/ob/api'

    def __init__(self, account, venue, api_key=None):
        self.account = account
        self.venue = venue

        if api_key is None:
            api_key = os.environ.get('API_KEY')

        self.session = requests.Session()
        self.session.headers.update({"X-Starfighter-Authorization": api_key})

        self.websocket_clients = []
        self.websocket_manager = WebSocketManager()

    def api_up(self):
        r = self.session.get(
                '{}/heartbeat'.format(self.base_url))
        return r.json()['ok']

    def venue_up(self):
        r = self.session.get(
                '{}/venues/{}/heartbeat'.format(
                    self.base_url, self.venue))
        return r.json()['ok']

    def stocks(self):
        r = self.session.get(
                '{}/venues/{}/stocks'.format(
                    self.base_url, self.venue))
        return r.json()['symbols']

    def orderbook(self, stock):
        r = self.session.get(
                '{}/venues/{}/stocks/{}'.format(
                    self.base_url, self.venue, stock))
        return r.json()

    def order(self, stock, price, qty, direction, order_type):
        data = {
            'account': self.account,
            'price': price,
            'qty': qty,
            'direction': direction,
            'orderType': order_type
        }
        r = self.session.post(
                '{}/venues/{}/stocks/{}/orders'.format(
                    self.base_url, self.venue, stock),
                json=data)
        return r.json()

    def quote(self, stock):
        r = self.session.get(
                '{}/venues/{}/stocks/{}/quote'.format(
                    self.base_url, self.venue, stock))
        return r.json()

    def order_status(self, order_id, stock):
        r = self.session.get(
                '{}/venues/{}/stocks/{}/orders/{}'.format(
                    self.base_url, self.venue, stock, order_id))
        return r.json()

    def cancel(self, order_id, stock):
        r = self.session.delete(
                '{}/venues/{}/stocks/{}/orders/{}'.format(
                    self.base_url, self.venue, stock, order_id))
        return r.json()

    def orders(self, stock=None):
        if stock is None:
            url = '{}/venues/{}/accounts/{}/orders'.format(
                    self.base_url, self.venue, self.account)
        else:
            url = '{}/venues/{}/accounts/{}/stocks/{}/orders'.format(
                    self.base_url, self.venue, self.account, stock)
        r = self.session.get(url)
        return r.json()


    class WebSocketClient(WebSocketBaseClient):
        def __init__(self, url, callback, websocket_manager):
            WebSocketBaseClient.__init__(self, url)
            self.callback = callback
            self.websocket_manager = websocket_manager

        def handshake_ok(self):
            print('Connected to Stockfighter web socket server.')
            self.websocket_manager.add(self)

        def close(self, code, reason=None):
            print('Web socket closed.\nCode: {}\nReason: {}'.format(code, reason))

        def received_message(self, message):
            data = json.loads(message.data.decode('utf-8'))
            self.callback(data)

    def ticker(self, callback, stock=None):
        url = 'wss://api.stockfighter.io/ob/api/ws/{}/venues/{}/tickertape'.format(
                self.account, self.venue)
        if stock is not None:
            url += '/stocks/{}'.format(stock)
        self.websocket_clients.append(self.WebSocketClient(url, callback, self.websocket_manager))

    def executions(self, callback, stock=None):
        url = 'wss://api.stockfighter.io/ob/api/ws/{}/venues/{}/executions'.format(
                self.account, self.venue)
        if stock is not None:
            url += '/stocks/{}'.format(stock)
        self.websocket_clients.append(self.WebSocketClient(url, callback, self.websocket_manager))

    def start_websocket_clients(self):
        try:
            self.websocket_manager.start()
            for client in self.websocket_clients:
                client.connect()

            while True:
                for ws in self.websocket_manager.websockets.values():
                    if not ws.terminated:
                       break
                else:
                    break
                time.sleep(3)
        except KeyboardInterrupt:
            self.shutdown_websocket_clients()

    def shutdown_websocket_clients(self):
        self.websocket_manager.close_all()
        self.websocket_manager.stop()
        self.websocket_manager.join()
