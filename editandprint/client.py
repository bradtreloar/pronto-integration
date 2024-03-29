
import requests
from bs4 import BeautifulSoup
from common.exceptions import OrderNotFoundException

from editandprint.order_parser import check_order_exists, parse_order


class WebClient:

    def __init__(self, auth):
        self.base_url = "https://shop.allbizsupplies.biz"
        self.auth = auth
        self.session = requests.Session()

    def refresh_session(self):
        login_url = self.base_url + "/admin/index.php"
        form = {
            "username": self.auth["username"],
            "password": self.auth["password"],
            "login": "Login"
        }
        self.session.post(login_url, data=form, allow_redirects=False)

    def get_order_html(self, oid):
        url = self.base_url + "/admin/order_action.php"
        params = {
            "Action": "edit_order",
            "OrderId": str(oid)
        }
        response = self.session.get(url, params=params, allow_redirects=True)
        if response.status_code != 200:
            raise OrderNotFoundException(oid)
        soup = BeautifulSoup(response.text, "html.parser")
        if soup.title.text == "Admin :: Login":
            self.refresh_session()
            return self.get_order_html(oid)
        return response.text

    def get_order(self, oid):
        order_html = self.get_order_html(oid)
        check_order_exists(order_html, oid)
        order = parse_order(order_html).get_pronto_format()
        order["reference"] = oid
        return order
