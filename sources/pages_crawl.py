from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options
from collections import defaultdict

import time
import pandas as pd
import sys
import enchant
import re

DELAY_TIME = 3
OUTPUT_FILE = '../inputs/verified_page3.csv'
QUEUE_FILE = '../inputs/queue_page.csv'
LOG_FILE = '../logs/log_page_crawl.dat'
LIMIT_PAGE = 1000
LIMIT_CLICK = 3
ENG_THRESH = 0.7
R = re.compile(r'[a-zA-Z]+')

def clean_page_link(link):
	splited = link.split('/')
	joined = '/'.join(splited[:-1])
	return joined


def start_driver():

    global driver

    options = Options()
    options.add_argument("--disable-notification")
    options.add_argument("--disable-infobars")
    options.add_argument("--mute-audio")
    options.add_argument("--disable-extensions")
    options.add_experimental_option("prefs", { 
    "profile.default_content_setting_values.notifications": 2
	})
    #options.add_argument("headless")

    driver = webdriver.Chrome(options=options)


def login(email, password):
    """ Logging into our own profile """

    try:
        driver.get('https://facebook.com')

        driver.find_element_by_name('email').send_keys(email)
        driver.find_element_by_name('pass').send_keys(password)
        driver.find_element_by_xpath('//input[@aria-label="Log In"]').click()

        time.sleep(DELAY_TIME)

    except Exception as e:
        print('Error in Login')
        print(e)
        exit()


def save_csv(total_link_page, out_file):
	total_link_page = pd.DataFrame(list(total_link_page.items()), columns=['link','state'])
	total_link_page.to_csv(out_file)


def check_verified(feed_page):
	basic_facebook_link = convert_input_user(feed_page)

	# Move to basic form of facebook
	driver.get(basic_facebook_link)

	# Find Verified mark
	try:
		driver.find_element_by_xpath("//span[@aria-label='Verified Page']")
		print('VERIFIED')
		return True

	except NoSuchElementException:
		print('UN-VERIFIED\n'.format(feed_page))
		return False

def check_english(feed_page):
	basic_facebook_link = convert_input_user(feed_page)

	# Move to basic form of faecbook
	driver.get(basic_facebook_link)

	# Load English dictionary
	d = enchant.Dict('en_US')

	# Take first 5 post
	posts = [e.get_attribute('href') for e in driver.find_elements_by_xpath("//a[contains(text(), 'Full Story')]")]

	def check(text):
		return d.check(text)

	# Travel to post
	final_percent = 0
	total_content = 0
	for p in posts:
		# Go to post
		driver.get(p)

		# Get content from post
		content = [e.text for e in driver.find_elements_by_xpath("//div[@data-ft='{\"tn\":\"*s\"}']")]
		if len(content) == 0:
			content = [e.text for e in driver.find_elements_by_xpath("//div[@class='_2vj8']")]

		if len(content) > 0:
			total_content += 1
			# Go through each text in content
			for c in content:
				post_percent = 0
				line = 0
				if c is not "":
					c = R.findall(c)
					result = map(check, c)
					result = list(result)
					
					# Percent english words in 1 line of content
					if len(result) == 0:
						c = 0
						line -= 1
					else: 
						c = sum(result) / len(result)

					# Sum per content
					post_percent += c

					# None empty content
					line += 1

			# Calculate final percent
			# Case for just picture in post, will not count
			if line == 0:
				post_percent = 0
				total_content -= 1
			else:
				post_percent /= line
			final_percent += post_percent 

	if total_content == 0:
			final_percent = 0
	else:
		final_percent /= total_content
	
	print(final_percent)
	if final_percent >= ENG_THRESH:
		print('ENGLISH\n')
		return True
	else: 
		print('NON-ENGLISH\n')
		return False

def scrap_pages(feed_page, queue_link_page):
	print(feed_page)

	if not check_verified(feed_page):
		return False
	if not check_english(feed_page):
		return False

	driver.get(feed_page)
	time.sleep(DELAY_TIME)

	click = 0
	while click < LIMIT_CLICK:
		try:	
			driver.find_element_by_xpath('//a[@class="_g3j"]').click()
			break
		except ElementClickInterceptedException:
			time.sleep(DELAY_TIME)
		except NoSuchElementException:
			return False
		click += 1

	time.sleep(DELAY_TIME)
	link_page = driver.find_elements_by_xpath('//div[@class="fsl fwb fcb"]//a')
	[queue_link_page[clean_page_link(l.get_attribute('href'))] for l in link_page]
	return True

def convert_input_user(input_user):
    facebook_user_link = input_user.split('.')
    facebook_user_link[0] = 'https://mbasic'
    facebook_user_link = ('.').join(facebook_user_link)
    return facebook_user_link


def papes_crawl(feed_page):
	# Init
	total_link_page = {}
	total_link_page = defaultdict(lambda:True, total_link_page)

	# Queue
	queue_link_page = {}
	queue_link_page = defaultdict(lambda:True, queue_link_page)

	# Set 1st page and make queue
	total_link_page[feed_page]
	scrap_pages(feed_page, queue_link_page)
	save_csv(total_link_page, OUTPUT_FILE)

	pos = 0
	while True:
		try:
			temp_link = list(queue_link_page)
			if scrap_pages(temp_link[pos], queue_link_page):
				total_link_page[temp_link[pos]]
				save_csv(total_link_page, OUTPUT_FILE)
				save_csv(queue_link_page, QUEUE_FILE)

			if len(total_link_page) >= LIMIT_PAGE:
				print('Reach limit')
				driver.close()
				break
			pos += 1
		except IndexError as e:
			print('ERROR: {}\n'.format(sys.exc_info()))
			break
	

def main():
	# Init
    start_driver()
    # Must marked and english
    feed_page = 'https://www.facebook.com/JennyMcCarthyOfficial'

    # Sign in information
    email = 'working.nook@gmail.com'
    password = 'TTrungT1nG1st'
    login(email, password)

    # Crawl pages
    papes_crawl(feed_page)


if __name__ == '__main__':
	sys.stdout = open(LOG_FILE, 'w', encoding='utf-8')
	main()
	sys.stdout.close()