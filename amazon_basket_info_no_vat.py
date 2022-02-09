from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException      

from easygui import *
import sys

## Sets up driver
options = webdriver.ChromeOptions()
prefs = {"profile.default_content_setting_values.notifications" : 2}
options.add_experimental_option("prefs",prefs)
options.add_argument('headless')              # USE THESE SETTINGS
options.add_argument('window-size=1920x1080') # USE THESE SETTINGS
driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(30)
#driver.maximize_window()  #TESTING ONLY
delay = 5
driver.get("https://www.amazon.co.uk/")

## Set up details
email = "jake.burroughs@freshcut.biz"
password = "Flowers123"
item_list = []
quantity_list = []
price_list_nc = [] #Not calculated

def main(email,password,item_list,quantity_list,price_list_nc):
    sign_in(email,password)
    nav_to_cart()
    item_list = get_item_names(item_list)
    quantity_list = get_quantity_list(quantity_list)
    price_list = get_price_list(price_list_nc,quantity_list)
    sub_total = get_sub_total()
    verifiy_prices(price_list,sub_total)
    basket_list = list(zip(item_list,quantity_list,price_list))
    print (basket_list)
    
def sign_in(email,password):
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,"nav-link-accountList"))).click()
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,"ap_email"))).send_keys(email)
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,"continue"))).click()
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,"ap_password"))).send_keys(password)
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,"signInSubmit"))).click()

def nav_to_cart():
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,"nav-cart"))).click()

def get_item_names(item_list):
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.CLASS_NAME,'a-truncate-cut')))
    all_items = driver.find_elements(By.XPATH,"//span[contains(@class,'a-truncate-full a-offscreen')]")
    for item in all_items:
        item_list.append(item.get_attribute("textContent"))
    return item_list

def get_quantity_list(quantity_list):
    all_quantity = driver.find_elements(By.XPATH,"//span[contains(@class,'a-dropdown-prompt')]")
    for item_quantity in all_quantity:
        quantity_list.append(item_quantity.get_attribute("textContent"))
    return quantity_list

def get_price_list(price_list_nc,quantity_list):
    price_list = []
    all_prices = driver.find_elements(By.XPATH,"//span[contains(@class,'a-size-medium a-color-base sc-price sc-white-space-nowrap sc-product-price sc-price-vat-excluded a-text-bold')]")
    for item_price in all_prices:
        price_list_nc.append(item_price.get_attribute("textContent"))
    price_list_nc = [p.replace("£","") for p in price_list_nc]
    price_list_nc = [float(p) for p in price_list_nc]
    quantity_list = [float(q) for q in quantity_list]
    for p,q in zip(price_list_nc,quantity_list):
        price_list.append(p*q)
    return price_list

def get_sub_total():
    sub_total = driver.find_element(By.XPATH,"//span[contains(@class,'a-size-medium a-color-base sc-price sc-white-space-nowrap')]").text
    sub_total = sub_total.replace("£","")
    return sub_total

def verifiy_prices(price_list,sub_total):
    price_total = float((sum(price_list)) * 11.2)
    sub_total = float(sub_total)
    numerator = price_total - sub_total
    denominator = (price_total + sub_total) / 2
    difference = abs((numerator / denominator) * 100)
    if difference > 0.03:
        print ("price difference too great")

   
    
main(email,password,item_list,quantity_list,price_list_nc)
