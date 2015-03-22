import urllib.parse

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
import requests

from common import Account

class SantanderAccount(Account):
	def __init__(self, sort_code, account_no):
		super().__init__(sort_code, account_no)
		self.auth(None, None, None, {})

	def auth(self, user, password, reg_num, secrets):
		self.user = user
		self.password = password
		self.reg_num = reg_num
		self.secrets = secrets

	def get_qif_statement(self, from_date, to_date):
		driver = webdriver.PhantomJS()

		driver.get('https://retail.santander.co.uk/LOGSUK_NS_ENS/BtoChannelDriver.ssobto?dse_operationName=LOGON&dse_processorState=initial&redirect=S')

		driver.implicitly_wait(3)
		elem = driver.find_element_by_id('infoLDAP_E.customerID')
		elem.send_keys(self.user)
		elem.send_keys(Keys.RETURN)


		try:
			challenge = driver.find_element_by_css_selector('[id="cbQuestionChallenge.responseUser"]')
			question = driver.find_element_by_css_selector('form .form-item .data').text.strip()
			print("Verifying new computer: {}".format(question))
			challenge.send_keys(self.secrets.get(question) or input("Answer not known: "))
			challenge.send_keys(Keys.RETURN)
		except NoSuchElementException as e:
			print("Verification not needed?")

		try:
			phrase = driver.find_element_by_css_selector('.imgSection span')
			print(phrase.text.strip())
		except NoSuchElementException:
			print("No magic phrase")


		# login
		passcode_e = driver.find_element_by_id('authentication.PassCode')
		reg_num_e = driver.find_element_by_id('authentication.ERN')
		passcode_e.send_keys(self.password)
		reg_num_e.send_keys(self.reg_num)
		passcode_e.send_keys(Keys.RETURN)

		# list accounts
		accounts = (driver
			.find_element_by_css_selector('.accountlist')
			.find_elements_by_css_selector('li .info')
		)
		account_map = {
			tuple(acc.find_element_by_css_selector('.number').text.split(' ')): acc
			for acc in accounts
		}

		# choose our account
		acc = account_map[self.id]
		acc.find_element_by_css_selector('a').click()

		driver.find_element_by_css_selector('.download').click()

		Select(driver.find_element_by_css_selector('#sel_downloadto')).select_by_visible_text('Intuit Quicken (QIF)')


		from_day = driver.find_element_by_css_selector('[name="downloadStatementsForm.fromDate.day"]')
		from_month = driver.find_element_by_css_selector('[name="downloadStatementsForm.fromDate.month"]')
		from_year = driver.find_element_by_css_selector('[name="downloadStatementsForm.fromDate.year"]')

		from_day.clear()
		from_day.send_keys(str(from_date.day))
		from_month.clear()
		from_month.send_keys(str(from_date.month))
		from_year.clear()
		from_year.send_keys(str(from_date.year))


		to_day = driver.find_element_by_css_selector('[name="downloadStatementsForm.toDate.day"]')
		to_month = driver.find_element_by_css_selector('[name="downloadStatementsForm.toDate.month"]')
		to_year = driver.find_element_by_css_selector('[name="downloadStatementsForm.toDate.year"]')

		to_day.clear()
		to_day.send_keys(str(to_date.day))
		to_month.clear()
		to_month.send_keys(str(to_date.month))
		to_year.clear()
		to_year.send_keys(str(to_date.year))

		params, target_url, user_agent = driver.execute_script("""
			return (function() {
				var data = $('form').serializeArray();
				data.push({ name: 'downloadStatementsForm.events.0', value: 'Download' });
				return [$.param(data), $('form').attr('action'), navigator.userAgent];
			})();
		""")

		cookies = {
			c['name']: c['value']
			for c in driver.get_cookies()
		}

		r = requests.post(
			urllib.parse.urljoin(driver.current_url, target_url),
			data=params,
			cookies=cookies,
			headers = {
				'User-Agent': user_agent,
				'Referer': driver.current_url,
				'Content-Type': 'application/x-www-form-urlencoded'
			}
		)

		return r.content