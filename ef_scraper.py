import random
from requests import get
from bs4 import BeautifulSoup
import ast
from decimal import Decimal
from configparser import ConfigParser
import argparse
import logging
import os
from csv import DictWriter
from datetime import datetime
from sys import stdout

base_url = 'https://empireflippers.com'
index_endpoint = '/marketplace/'
pagination_endpoint = ''
pages = 10
use_proxy = False
p_host = 'p_host'
p_user = 'p_user'
p_pass = 'p_pass'
port = 'ports_here'
conn_pro = dict()
debug_mode = False


def check_create_dir(dirname):
    '''
    Checks if directory exists and if it doesn't creates a new directory
    :param dirname: Path to directory
    '''
    if not os.path.exists(dirname):
        if '/' in dirname:
            os.makedirs(dirname)
        else:
            os.mkdir(dirname)


def save_to_csv(cache_data, filename):
    logger = logging.getLogger('SaveFileCore')
    check_create_dir('scrape_cache')
    filepath = f'scrape_cache/{filename}.csv'
    logger.info('Writing results to file')
    with open(filepath, 'w') as f:
        for count, cache_ele in enumerate(cache_data):
            logger.debug(f'Writing row: {count + 1}')
            w = DictWriter(f, cache_ele.keys())
            if count == 0:
                logger.debug('Writing header')
                w.writeheader()
            w.writerow(cache_ele)


def get_user_agent():
    user_agents = list()
    with open('user_agents.txt', 'r') as f:
        for line in f:
            user_agents.append(line)
    return random.choice(user_agents).strip()


def get_graph(listing_endpoint):
    logger = logging.getLogger('GraphDataCore')
    graph_data = dict()
    if use_proxy:
        listing_resp = get(base_url + listing_endpoint, headers=ef_headers, timeout=10, proxies=conn_pro)
    else:
        listing_resp = get(base_url + listing_endpoint, headers=ef_headers, timeout=10)
    if listing_resp.status_code == 200:
        listing_soup = BeautifulSoup(listing_resp.content.decode('utf-8'), 'html.parser')
        description = ''
        for des_ele in listing_soup.find('div', {'class': 'listing-details'}).find_all('p'):
            description += des_ele.text.strip() + '\n'
        graph_data['Description'] = description
        t_button = listing_soup.find('div', {'class': 'twelve-month btn btn-white-transparent earnings-selector'})
        gross_earnings_list = t_button['data-earnings-gross'].strip()
        logger.debug(f'Gross earnings list: {gross_earnings_list}')
        net_earnings_list = t_button['data-earnings-profit'].strip()
        logger.debug(f'Net earnings list: {net_earnings_list}')
        gross_earnings = 0
        for g_ele in ast.literal_eval(gross_earnings_list):
            gross_earnings += Decimal(g_ele.strip())
        net_profit = 0
        for n_ele in ast.literal_eval(net_earnings_list):
            net_profit += Decimal(n_ele.strip())
        graph_data['Revenue'] = gross_earnings
        graph_data['EBITDA'] = net_profit
        logger.debug(f"Gross revenue: {gross_earnings}")
        logger.debug(f"Earnings profit: {net_profit}")
        return graph_data
    else:
        raise Exception('Could not get Graph data')


def get_listings(results_soup, index=False):
    ret = list()
    logger = logging.getLogger('ListingsCore')
    if index:
        for listing_cnt, listing_ele in enumerate(results_soup.find_all('div', {'class': 'listing-item new'})):
            try:
                listing_data = dict(agent_company='null', location='online', phone='null', cash_flow=0)
                logger.info(f'--- Getting result: {listing_cnt} ---')
                name = listing_ele.find('div', {'class': 'niches'}).text.strip()
                monetization = listing_ele.find('div', {'class', 'monetization-mobile'}).find('div', {'class': 'value'})\
                    .text.strip()
                logger.debug(f'Monetization: {monetization}')
                listing_data['Industry'] = f'{monetization} {name}'
                price = listing_ele.find('div', {'class': 'metric-item price'}).find('div', {'class': 'value'})\
                    .text.strip()
                listing_data['Asking Price'] = price
                logger.debug(f"Price: {price}")
                endpoint = listing_ele.find('a', {'class': 'btn btn-blue btn-small'})['href'].strip()
                logger.debug(f"Endpoint: {endpoint}")
                listing_data.update(get_graph(endpoint))
                ret.append(listing_data)
            except Exception as exc:
                logger.error('Could not get listing. Omitting')
                logger.debug(f'Details: {str(exc)}')
    else:
        for listing_cnt, listing_ele in enumerate(results_soup.find_all('div', {'class': 'listing-details'})):
            try:
                listing_data = dict(agent_company='null', location='online', phone='null', cash_flow=0)
                logger.info(f'--- Getting result: {listing_cnt} ---')
                name = listing_ele.find('div', {'class': 'niches'}).text.strip()
                logger.debug(f"Name: {name}")
                monetization = listing_ele.find('div', {'class', 'monetization-mobile'}).find('div', {'class': 'value'}) \
                    .text.strip()
                logger.debug(f'Monetization: {monetization}')
                listing_data['Industry'] = f'{monetization} {name}'
                price = listing_ele.find('span', {'class': 'listing-price'}).text.strip()
                logger.debug(f"Price: {price}")
                listing_data['Asking Price'] = price
                endpoint = listing_ele.find('a', {'class': 'btn btn-blue btn-small'})['href'].strip()
                logger.debug(f"Endpoint: {endpoint}")
                listing_data.update(get_graph(endpoint))
                ret.append(listing_data)
            except Exception as exc:
                logger.error('Could not get listing. Omitting')
                logger.debug(f'Details: {str(exc)}')
    return ret


print('Empire flippers Scraper')
print('Reading config')

# init config
try:
    config = ConfigParser()
    config.read('scraperconfig.ini')
    pages = int(config['search']['pages'])
    use_proxy = config.getboolean('proxy', 'use_proxy')
    p_user = config['proxy']['proxy_user']
    p_pass = config['proxy']['proxy_pass']
    p_host = config['proxy']['proxy_host']
    port = config['proxy']['proxy_port']
except Exception as exc:
    print('Cannot read config. Getting data from cmd only')
    print(f'Details: {str(exc)}')

parser = argparse.ArgumentParser(description='Automatically scrapes Trainline API for details about trains')
parser.add_argument('-p', dest='pgs', type=int, default=pages,
                    help='Number of pages to scrape')
parser.add_argument('--use_proxy', dest='use_proxy', action='store_true', default=use_proxy, help='Toggle proxy')
parser.add_argument('-p_host', dest='p_host', default=p_host, help='Enter proxy host')
parser.add_argument('-p_port', dest='p_port', default=port, help='Enter proxy port')
parser.add_argument('-p_user', dest='p_user', default=p_user, help='Enter proxy username')
parser.add_argument('-p_pass', dest='p_pass', default=p_pass, help='Enter proxy password')
parser.add_argument('--debug', dest='d_mode', action='store_true', default=debug_mode, help='Toggle proxy')
args = parser.parse_args()
use_proxy = args.use_proxy
p_host = args.p_host
port = args.p_port
p_user = args.p_user
p_pass = args.p_pass
pages = args.pgs
debug_mode = args.d_mode

rootLogger = logging.getLogger()
consoleHandler = logging.StreamHandler(stdout)
check_create_dir('logs')
log_timestamp = datetime.now()
fileHandler = logging.FileHandler(
    os.path.join('logs', 'EFScraper{0}.log'.format(log_timestamp.strftime('%m-%d-%y-%H-%M-%S'))), 'w',
    'utf-8')
fileHandler.setFormatter(logging.Formatter('%(asctime)s:-[%(name)s] - %(levelname)s - %(message)s'))
rootLogger.addHandler(consoleHandler)
rootLogger.addHandler(fileHandler)
rootLogger.setLevel(logging.DEBUG)
if debug_mode:
    consoleHandler.setLevel(logging.DEBUG)
else:
    consoleHandler.setLevel(logging.INFO)
fileHandler.setLevel(logging.DEBUG)
consoleHandler.setFormatter(logging.Formatter('[%(name)s] - %(levelname)s - %(message)s'))

rootLogger.debug(f'Pages: {pages}')
rootLogger.debug(f'use_proxy: {use_proxy}')
rootLogger.debug(f'Debug mode: {debug_mode}')

if use_proxy:
    p_port = random.choice(port.split(','))
    rootLogger.info(f"Using proxy: {f'https://{p_user}:{p_pass}@{p_host}:{p_port}'}")
    conn_pro['https'] = f'https://{p_user}:{p_pass}@{p_host}:{p_port}'
    conn_pro['http'] = f'http://{p_user}:{p_pass}@{p_host}:{p_port}'

ef_headers = {'user-agent': get_user_agent()}
index_url = base_url + index_endpoint
results_list = list()

if use_proxy:
    home_resp = get(index_url, headers=ef_headers, proxies=conn_pro)
else:
    home_resp = get(index_url, headers=ef_headers)
now = datetime.now()
if home_resp.status_code == 200:
    rootLogger.info('+++++++++++++++ Page: Index +++++++++++++++')
    index_soup = BeautifulSoup(home_resp.content.decode('utf-8'), 'html.parser')
    results_list += get_listings(index_soup, True)
else:
    rootLogger.error('Could not scrape index page')
for page_no in range(10):
    rootLogger.info(f'+++++++++++++++ Page: {page_no + 1} +++++++++++++++')
    page_url = f'https://empireflippers.com/wp-content/uploads/alm-cache/marketplace_load_more/page-{page_no + 1}' \
               f'.html'
    if use_proxy:
        page_resp = get(page_url, headers=ef_headers, proxies=conn_pro)
    else:
        page_resp = get(page_url, headers=ef_headers)
    if page_resp.status_code == 200:
        page_soup = BeautifulSoup(page_resp.content.decode('utf-8'), 'html.parser')
    elif page_resp.status_code == 404:
        rootLogger.info('404 found. Trying alternate endpoint')
        alt_page_endpoint = 'https://empireflippers.com/wp-admin/admin-ajax.php?id=marketplace_load_more&post_id' \
                            '=8&slug=marketplace&canonical_url=https://empireflippers.com/marketplace/&posts_per_' \
                            f'page=15&page={page_no}&offset=10&post_type=post&repeater=template_4&seo_start_page=' \
                            '1&preloaded=false&preloaded_amount=0&cache_id=marketplace_load_more&cache_logged_in' \
                            '=false&order=DESC&orderby=date&action=alm_get_posts&query_type=standard'
        if use_proxy:
            alt_page_resp = get(alt_page_endpoint, headers=ef_headers, proxies=conn_pro)
        else:
            alt_page_resp = get(alt_page_endpoint, headers=ef_headers)
        if alt_page_resp.status_code == 200:
            page_soup = BeautifulSoup(alt_page_resp.json()['html'], 'html.parser')
        else:
            rootLogger.error('alt fail')
            continue
    else:
        rootLogger.error('Could not scrape page')
        continue
    results_list += get_listings(page_soup)
if len(results_list) > 0:
    save_to_csv(results_list, f"{log_timestamp.strftime('%m-%d-%y-%H-%M-%S')}")
later = datetime.now()
rootLogger.info(f'Total time taken: {(later - now).seconds} seconds(s)')
rootLogger.info('Goodbye')


