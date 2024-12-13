from datetime import datetime, timedelta
from enum import Enum

from bs4 import BeautifulSoup
import requests
import json
import re
import time
import pandas as pd
import json
import numpy as np

class ProfitLossType(Enum):
    ACCOMPLISHED = 'accomplished'
    UNACCOMPLISHED = 'unaccomplished'
    
    
class VirtualStockAccount():

    def __init__(self, email, password, wait_time=1):

        """
        輸入帳號(email)密碼(password)來登入，並設定每個request的延遲時間是wait_time

        """
        login_url = 'https://www.cmoney.tw/identity/account/login'
        two_factor_url = "https://www.cmoney.tw/identity/account/login/two-factor-options"
#         headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
#             'Referer': login_url
#         }
        self.ses = requests.Session()
        res = self.ses.get(login_url)#, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Extract the CSRF token from the login page
        csrf_token = soup.find('input', {'name': '__RequestVerificationToken'})['value']

        self.wait_time = wait_time
        
        time.sleep(self.wait_time)

        res = self.ses.post(login_url, data={ # , headers=headers
            # '__VIEWSTATE': viewstate[18:],
            # '__EVENTVALIDATION': eventvalidation[24:],
            'Account': email,
            'Password': password,
            '__RequestVerificationToken': csrf_token,
            'RememberMe': 'true',
            'ClientId': 'cmmainweb',
            'RedirectUri': '/member/login/signin-oidc.aspx',
            'ReturnUrl': '~/authorize/callback?client_id=cmmainweb&redirect_uri=https://outpost.cmoney.tw/member/login/signin-oidc.aspx&response_type=none&scope=',
            'LogoUri': 'https://image.cmoney.tw/servicetest/swagger/1675180800/d1202faa-8464-4a42-a77e-eb16348f8508.png'
        })
        time.sleep(self.wait_time)
        
        # Check if 2FA page is encountered
        if '透過雙重認證保護您的帳戶' in res.text:
            soup = BeautifulSoup(res.text, 'html.parser')

            # Extract CSRF token from 2FA page
            csrf_token_2fa = soup.find('input', {'name': '__RequestVerificationToken'})['value']
            return_url = soup.find('input', {'name': 'ReturnUrl'})['value'] if soup.find('input', {'name': 'ReturnUrl'}) else ''#'~/authorize/callback?client_id=cmmainweb&amp;redirect_uri=https://outpost.cmoney.tw/member/login/signin-oidc.aspx&amp;response_type=none&amp;scope='
            remember_me = soup.find('input', {'name': 'RememberMe'})['value'] if soup.find('input', {'name': 'RememberMe'}) else 'true'
            # Bypass Two-Factor Authentication
            two_factor_payload = {
                'DontAskAgain': 'true',     # Don't ask again
                'IsEnable': 'false',        # Skip enabling 2FA
                '__RequestVerificationToken': csrf_token_2fa,
                'ReturnUrl': return_url,    # Add the required ReturnUrl
                'RememberMe': remember_me
            }

            # Submit the 2FA bypass request
            res = self.ses.post(two_factor_url, data=two_factor_payload)#, headers=headers
            print("Login successful after bypassing 2FA!")

        else:
            print("Login successful without 2FA.")

        res = self.ses.get('https://www.cmoney.tw/vt/main-page.aspx')
        
        # Parse the response content
        soup = BeautifulSoup(res.text, 'html.parser')
        # Extract ChooseMemberId and __RequestVerificationToken
        choose_member_id = soup.find('input', {'id': 'ChooseMemberId'}).get('value', '')
        request_verification_token = soup.find('input', {'name': '__RequestVerificationToken'}).get('value', '')
        return_url = soup.find('input', {'name': 'ReturnUrl'})['value'] if soup.find('input', {'name': 'ReturnUrl'}) else ''

        # Send the form submission request
        submit_url = 'https://www.cmoney.tw/identity/account/select'
        form_data = {
            'ChooseMemberId': choose_member_id,
            '__RequestVerificationToken': request_verification_token,
            'ReturnUrl': return_url,
        }

        # Send the POST request
        res = self.ses.post(submit_url, data=form_data)
        
        res = self.ses.get('https://www.cmoney.tw/vt/main-page.aspx')
        aids = re.findall('aid=[\d]*', res.text )
        aids = [a.split('=')[1] for a in aids]
        aids = [a for a in aids if a.isdigit()]
        self.aids = aids
        if self.aids:
            self.aid = aids[0]
            print('accounts', aids)
            print('current account', self.aid)
        else:
            print('Require manually set account ID')
#             raise Exception('Cannot open account due to incorrect account name or password')

    def get_price(self, sid):

        """
          輸入sid='1101'，會拿到以下的資料：
           {'StockInfo': {'Commkey': '1101',
          'Name': '台泥',
          'MarketType': 2,
          'RefPrice': 42.9,
          'CeilPrice': 47.15,
          'FloorPrice': 38.65,
          'SalePrice': 43.1,
          'TotalQty': 8665,
          'DecimalPoint': 1,
          'LowPr': 42.6,
          'BuyPr1': 43.05,
          'SellPr1': 43.1,
          'BuyPr2': 43.0,
          'SellPr2': 43.15,
          'BuyPr3': 42.95,
          'SellPr3': 43.2,
          'BuyPr4': 42.9,
          'SellPr4': 43.25,
          'BuyPr5': 42.85,
          'SellPr5': 43.3,
          'BuyQty1': 73.0,
          'SellQty1': 43.0,
          'BuyQty2': 459.0,
          'SellQty2': 42.0,
          'BuyQty3': 111.0,
          'SellQty3': 178.0,
          'BuyQty4': 169.0,
          'SellQty4': 120.0,
          'BuyQty5': 46.0,
          'SellQty5': 230.0,
          'DealTime': '2018-08-22T11:40:53',
          'OrderTime': '2018-08-22T11:40:53'},
         'SalePrice': '43.1',
         'IsWarrant': False}
        """
        res = self.ses.get('https://www.cmoney.tw/vt/ashx/HandlerGetStockPrice.ashx', params={
            'q': sid,
            'accountType': 1,
            'isSDAndSell': 'false',
            })
        return json.loads(res.text)

    def entrust(self, sid, price, quantity, tradekind, type_):
        res = self.ses.get('https://www.cmoney.tw/vt/ashx/userset.ashx', params={
            'act': 'NewEntrust',
            'aid': self.aid,
            'stock': sid,
            'price': price,
            'ordqty': quantity,
            'tradekind': tradekind,
            'type': type_,
            'hasWarrant': 'true',
        })

    def buy(self, sid, quantity, price='漲停'):

        """
        購買兩張台泥股票:
        例如sid='1101', quantity=2
        假如沒有輸入price就是以當前價格買入
        假如輸入了price就是限價買入
        """

        self.entrust(sid, price, quantity, tradekind='c', type_='b')


    def sell(self, sid, quantity, price='跌停'):

        """
        賣出兩張台泥股票:
        例如sid='1101', quantity=2
        假如沒有輸入price就是以當前價格買入
        假如輸入了price就是限價買入
        """

        self.entrust(sid, price, quantity, 'c', 's')

    def sellshort(self, sid, quantity, price='跌停'):
        self.entrust(sid, price, quantity, 'sd', 's')

    def buytocover(self, sid, quantity, price='漲停'):
        self.entrust(sid, price, quantity, 'sd', 'b')

    def status(self):

        """
        查看目前account的狀態：
        [{'Id': '1101',
          'Name': '台泥',
          'TkT': '現股',
          'NowPr': '43.05',
          'DeAvgPr': '43.20',
          'IQty': '1',
          'IncomeLoss': '-402',
          'Ratio': '-0.93',
          'Cost': '43,200.00',
          'ShowCost': '43,200.00',
          'TodayQty': '0',
          'BoardLostSize': '1000',
          'IsWarrant': '0'}]
        """

        res = self.ses.get('https://www.cmoney.tw/vt/ashx/accountdata.ashx', params={
            'act': 'InventoryDetail',
            'aid': self.aid,
            '_': '1572343162391'
        })
        print(res.text)
        return json.loads(res.text)

    def listEntrust(self, f, s):

        for sid, q in s.items():
            if q == 0:
                continue
            print('new entrust', sid, q)

            f(sid.split()[0], abs(int(q)))
            time.sleep(self.wait_time)

    def get_orders(self):

        """拿到當下的委託"""

        res = self.ses.get('https://www.cmoney.tw/vt/ashx/accountdata.ashx', params={
            'act': 'EntrustQuery',
            'aid': self.aid,
        })

        return json.loads(res.text)

    def cancel_all_orders(self):

        """清空當下的委託"""

        orders = self.get_orders()
        time.sleep(self.wait_time)
        for o in orders:
            if o['CanDel'] == '1':
                print('Cancel order', o['Id'])
                res = self.ses.get('https://www.cmoney.tw/vt/ashx/accountdata.ashx', params={
                    'act': 'DeleteEntrust',
                    'aid': self.aid,
                    'GroupId': 0,
                    'OrdNo': o['CNo'],
                })
                time.sleep(self.wait_time)

    def rebalance(self, newlist):

        """
        將持股更新成newlist，newlist的結構可以參考buy_list的input，是一樣的。
        """

        newlist = pd.Series(newlist).astype(int)
        newlist.index = pd.Series(newlist.index).astype(str)

        status = self.status()
        if len(status):
            df = (pd.DataFrame(status)[['Id', 'IQty', 'NowPr', 'ShowCost', 'Ratio', 'TkT']]).sort_values('Id')
            df['Id'] = df['Id'].astype(str)
        else:
            df = pd.DataFrame(columns=['Id', 'IQty', 'NowPr', 'ShowCost', 'Ratio', 'TkT'])

        ## 現股
        def rebalance_type(tkt, newlist, long_entrust, short_entrust):

            df_c = df[df['TkT'] == tkt]
            oldlist_c = pd.Series(df_c['IQty'].values, index=df_c['Id'].values).astype(int)

            def calc_diff(new, old):
                new2 = new.reindex(old.index | new.index).fillna(0)
                old2 = old.reindex(old.index | new.index).fillna(0)
                return new2 - old2

            print("------- TEST S ---------")
            print(newlist)
            print("------- TEST E ---------")
            print(oldlist_c)
            print("----------------")

            diff_c = calc_diff(newlist, oldlist_c)
            """
            print("check diff -------------------------")
            print(newlist)
            print(oldlist_c)
            print(diff_c)
            print("check diff -------------------------")
            """
            print('------------------------------------------')
            print('operaetions', tkt)
            print("enter")
            print(diff_c[diff_c > 0])
            print("exit")
            print(diff_c[diff_c < 0])
            print('------------------------------------------')
            #input()
            self.listEntrust(long_entrust, diff_c[diff_c > 0])
            self.listEntrust(short_entrust, diff_c[diff_c < 0])

        rebalance_type('現股', newlist[newlist >= 0], self.buy, self.sell)
        rebalance_type('融券', -newlist[newlist <= 0], self.sellshort, self.buytocover)



    def info(self):

        res = self.ses.get('https://www.cmoney.tw/vt/ashx/accountdata.ashx?act=AccountInfo&aid=%s&_=1572343162391' % self.aid)


        account_info = json.loads(res.text)
        return account_info

    def calculate_weight(self, position, lowest_fee=20, discount=1, add_cost=10, short=False):

        # get total money
        account_info = self.info()
        money = int(account_info['AllAssets'].replace(',', ''))

        print('total money', money)

        # get price of the stock
        import time
        infos = {}
        if isinstance(position, pd.DataFrame):
            slist = position.iloc[-1][(position.iloc[-1] != 0)].index.tolist()
        elif isinstance(position, pd.Series):
            slist = position[(position != 0)].index.tolist()
        elif isinstance(position, list):
            slist = position
        else:
            raise Exception("type of position should be pd.Series or list")

        for sid in slist:
            print(sid)
            infos[sid] = self.get_price(sid) # RefPrice
            time.sleep(2)

        # format dataframe and series
        price = pd.Series({sid:info['StockInfo']['RefPrice'] for sid, info in infos.items() if info is not None})
        none_stock_ids = [sid for sid, info in infos.items() if info is None]
        if none_stock_ids:
            print('**WARRN: there are stock cannot find info', none_stock_ids)

        stock_list = price.dropna().transpose()

        # rebalance stocks
        while (money / len(stock_list)) < (lowest_fee - add_cost) * 1000 / 1.425 / discount:
            stock_list = stock_list.loc[stock_list != stock_list.max()]

        while True:
            invest_amount = (money / len(stock_list))
            ret = np.floor(invest_amount / stock_list / 1000)

            if (ret == 0).any():
                stock_list = stock_list.loc[stock_list != stock_list.max()]
            else:
                break

        if isinstance(short, bool) and short == True:
            ret = -ret
        elif isinstance(short, list) and short:
            for s in short:
                ret[s] = -ret[s]


        ret.to_csv('position' + str(self.aid) + '.csv')
        slist = ret.to_dict()
        return slist

    def sync(self, *arg1, short=False, **arg2):
        slist = self.calculate_weight(*arg1, short=short, **arg2)
        self.rebalance(slist)

    
    def profit_loss(self, profitLossType: ProfitLossType,
                    startTime: str = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d"),
                    endTime: str = datetime.now().strftime("%Y-%m-%d")):

        """
       輸入損益類型(profitLossType)
       profitLossType => ProfitLossType.ACCOMPLISHED: "已實現損益"
       profitLossType => ProfitLossType.UNACCOMPLISHED: "未實現損益"
       """
        params = {
            'act': 'ProfitLoss',
            'aid': self.aid,
            'profitLossType': profitLossType.value
        }
        if profitLossType == ProfitLossType.ACCOMPLISHED:
            params["startTime"] = startTime
            params["endTime"] = endTime

        res = self.ses.get('https://www.cmoney.tw/vt/ashx/accountdata.ashx', params=params)
        return json.loads(res.text)
