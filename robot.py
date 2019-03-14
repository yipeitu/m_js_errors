from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote_plus
import traceback
import requests, urllib.parse
import csv
import json
from datetime import datetime
import os

SLACK_DICT = {
	'token': 'xoxp-89329937920-382773936513-577370058179-2ea5eaf22ea814bc3adc6a2aa5738a2f',
	'channel': 'GGZHKTGMB',
	'text': '',
	'username': 'bot'
}
SLACK_URL = 'https://slack.com/api/chat.postMessage'
SLACK_NOTIFY = True
ERROR_COUNT = 0
URL_LIST = ['wiktionary',
'google', 
'youtube', 
'wikipedia', 
'baike.baidu.com']

def send_msg_slack(message):
	try:
		if not SLACK_NOTIFY:
			print(message)
			return
		SLACK_DICT['text'] = message
		r = requests.post(SLACK_URL, urllib.parse.urlencode(SLACK_DICT), headers={'Content-Type':'application/x-www-form-urlencoded'})
	except Exception as e:
		print(e)
		print(traceback.format_exc())


def get_search_url(query, page_num=0, per_page=10, lang='zh-TW'):
	query = quote_plus(query)
	url = 'https://www.google.hr/search?q={}&num={}&start={}&nl={}'.format(query, per_page, page_num*per_page, lang)
	return url


def get_right_href(driver, search_string, page_num):
	global URL_LIST
	try:
		driver.get(get_search_url(search_string, page_num))
		WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'search')))
		a_list=driver.find_elements_by_xpath("//div[@id='search']//a")
		for element in a_list:
			href = element.get_attribute("href")
			b_rtn = True
			for url in URL_LIST:
				if href.find(url) != -1:
					b_rtn = False
			if b_rtn:
				URL_LIST += [href.split("/")[2]]
				return href
	except Exception as e:
		send_msg_slack(str(e)+"\n"+str(traceback.format_exc()))
	return ''

def write_to_csv(search_string, url, error_msg):
	global ERROR_COUNT
	try:
		with open("result.csv", "a") as f:
			cw = csv.writer(f, delimiter=",")
			cw.writerow([search_string, url, error_msg, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
			ERROR_COUNT += 1
	except Exception as e:
		send_msg_slack(str(e)+"\n"+str(traceback.format_exc()))

capabilities = DesiredCapabilities.CHROME
capabilities['loggingPrefs'] = { 'browser':'ALL' }

driver = webdriver.Chrome(desired_capabilities=capabilities)

try:
	fss = open("search_strings.json", "r")
	search_list = json.load(fss)
	done_list = []
	if os.path.isfile("search_done.json"):
		dict_done = json.load(open("search_done.json", "r"))
		done_list = dict_done.get("string", [])
		URL_LIST = dict_done.get("href", URL_LIST)
		search_list = list(set(search_list)-set(done_list))
	with open("search_done.csv", "a") as fw:
		cw = csv.writer(fw, delimiter=",")
		cw.writerow(["Start", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
		send_msg_slack("Start:"+datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
		for search_string in search_list:
			if ERROR_COUNT > 100:
				break
			# wait 10 seconds
			href = ""
			page_num = 0
			while len(href) == 0:
				href = get_right_href(driver, search_string, page_num)
				page_num += 1
				if page_num > 10:
					break
			if len(href) == 0:
				send_msg_slack("len(href) == 0: "+search_string)
			else:
				try:
					driver.implicitly_wait(10)
					driver.get(href)
					for entry in driver.get_log('browser'):
						if entry.get("level") == 'SEVERE':
							write_to_csv(search_string, href, entry.get('message'))
							break
				except Exception as e:
					send_msg_slack(str(e)+"\n"+str(traceback.format_exc()))
			done_list += [search_string]
			with open("search_done.json", "w") as fsd:
				json.dump({"string": done_list, "href": URL_LIST}, fsd)
			cw.writerow([str(ERROR_COUNT)+"/"+str(len(done_list)),datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
			send_msg_slack(str(ERROR_COUNT)+"/"+str(len(done_list))+" : "+datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
except Exception as e:
	send_msg_slack(str(e)+"\n"+str(traceback.format_exc()))
finally:
	driver.quit()
with open("search_done.csv", "a") as fw:
	cw = csv.writer(fw, delimiter=",")
	cw.writerow(["End", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
