from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException        

from time import sleep
from easygui import *
from datetime import datetime
import sys

## Sets up driver
options = webdriver.ChromeOptions()
prefs = {"profile.default_content_setting_values.notifications" : 2}
options.add_experimental_option("prefs",prefs)
#options.add_argument('headless')              # USE THESE SETTINGS
#options.add_argument('window-size=1920x1080') # USE THESE SETTINGS
driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(30)
driver.maximize_window()  #TESTING ONLY
delay = 3
driver.get("https://fc-not-app01:8637/VisionRecipe")


## Set up default inputs
product_code = "ING00002"
standard_quantity = "100"
time = "12:00 PM"
today = datetime.today()
date = today.strftime("%d/%m/%Y")
number_of_orders = "1"
username = "HJSimpson"
password = "password"
jobs_completed = 0

## CSS attributes
block = "block"

## Input fields for GUI
code = "WIP04499" # WIP04499 # BRANSTON001


def input_details(product_code,standard_quantity,date,time,number_of_orders,username,password): ## Build GUI input
    text = "Enter the following details"
    title = "Vision Manufacturing Job Fast Input"
    input_list = ["Product Code", "Standard Quantity", "Date","Time", "Number of Orders","Username","Password"]
    default_list = [product_code,standard_quantity,date,time,number_of_orders,username,password]   
    output = multpasswordbox(text, title, input_list, default_list)
    product_code,standard_quantity,date,time,number_of_orders,username,password = output[0],output[1],output[2],output[3],output[4],output[5],output[6]
    return product_code,standard_quantity,date,time,number_of_orders,username,password

def input_user_log_in_details(product_code,standard_quantity,date,time,number_of_orders,username,password):
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,"Username"))).clear()
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,"Username"))).send_keys(username)
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,"Password"))).clear()
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,"Password"))).send_keys(password)
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.XPATH,"//button[text()='Login']"))).click()
    return product_code,standard_quantity,date,time,number_of_orders,username,password

def check_password(product_code,standard_quantity,date,time,number_of_orders,username,password,jobs_completed):
    try:
        driver.find_element(By.XPATH,"/html/body/div[1]/div[2]/div[2]/div/div/div/form/div[1]/div/div[4]/div")
    except NoSuchElementException:
        print ("****LOG IN DETAILS CORRECT****")
        jobs_completed += 1
        return jobs_completed
    else:
        message = (f"The username ({username}) or password you supplied is incorrect, please re-enter or press cancel")
        title = "Error"
        output = ccbox(message, title)
        if output:
            main(product_code,standard_quantity,date,time,number_of_orders,username,password,jobs_completed)
        else:
            sys.exit()


def navigate_to_inputs():
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.XPATH,"//*[@id='navbarTogglerDemo02']/ul/li[2]"))).click()
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.XPATH,"//*[@id='navbarTogglerDemo02']/ul/li[2]/ul/li[1]"))).click()
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.XPATH,"//a[contains(text(),'Intake')]"))).click() 
    sleep(0.2) ## Search is slow

def input_product_code(product_code):
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'PageSearch_Code'))).send_keys(product_code)
    WebDriverWait(driver,15).until(EC.presence_of_element_located((By.CLASS_NAME,'SelectProduct'))).click()
    sleep(0.2) ### Lightbox closing has animation
    
def input_standard_quantity(standard_quantity):
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'StandardQuantity'))).clear()
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'StandardQuantity'))).send_keys(standard_quantity)
    print (f"(****STANDARD QUANTITY SET TO [{standard_quantity}] ****)")
    
def units_of_measure():
    try:
        temp = Select(WebDriverWait(driver,delay).until((EC.presence_of_element_located((By.ID,'ddlUOMs')))))
        grab_uom = temp.first_selected_option
    except:
        print (f"(****UOM NOT SET FOR [{code}]****)")
    else:
        temp = grab_uom.text
        print (f"(****UOM SET TO [{temp}] for [{code}]****)")

def specify_process():
    try:
        temp = Select(Select(WebDriverWait(driver,delay).until((EC.presence_of_element_located((By.ID,'ddlProcesses'))))))
        grab_sp = temp.first_selected_option
    except:
        print (f"(****PROCESS NOT SPECIFIED FOR [{code}]****)")
    else:
        temp = grab_sp.text
        print (f"(****PROCESS SPECIFIED TO [{temp}] for [{code}]****)")
        
def input_date(date):
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'ToBeSampledDate'))).clear()
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'ToBeSampledDate'))).send_keys(date)
    print (f"(****DATE SET TO [{date}] ****")

def input_number_of_orders(number_of_orders):
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'inputNumberOfOrders'))).clear()
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'inputNumberOfOrders'))).send_keys(number_of_orders)
    print (f"(****QUANTITY SET TO [{number_of_orders}]****)")

def quantity_by():
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'inputNumberOfOrders'))).clear()

def push_order():
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'btnCreateOrder'))).click()

def check_warnings():
##    sleep (2)
##    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'FailedJobs-tab'))).click()
    sleep(1)
    WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'Warnings-tab'))).click()
    parent = WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'dataWarnings')))
    sleep(0.2)
    warnings_text = parent.get_attribute('innerText')
    if warnings_text == "":
        WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'FailedJobs-tab'))).click()
        failed_parent = WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'dataFailedJobs')))
        sleep(0.2)
        warnings_text = failed_parent.get_attribute('innerText')
    if warnings_text == "":
        WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'SuccessfulJobs-tab'))).click()
        failed_parent = WebDriverWait(driver,delay).until(EC.presence_of_element_located((By.ID,'dataSuccessfulJobs')))
        sleep(0.2)
        warnings_text = failed_parent.get_attribute('innerText')
    return warnings_text
    
        
def display_output(product_code,standard_quantity,date,time,number_of_orders,username,password,warnings_text,jobs_completed ):
    ## message / information to be displayed on the screen
    if ccbox(warnings_text,"Job Completion Summary"):
        main(product_code,standard_quantity,date,time,number_of_orders,username,password,jobs_completed)
    else:
        sys.exit()
        
def main(product_code,standard_quantity,date,time,number_of_orders,username,password,jobs_completed):
    product_code,standard_quantity,date,time,number_of_orders,username,password = input_details(product_code,standard_quantity,date,time,number_of_orders,username,password)
    if jobs_completed == 0:
        input_user_log_in_details(product_code,standard_quantity,date,time,number_of_orders,username,password)
        jobs_completed = check_password(product_code,standard_quantity,date,time,number_of_orders,username,password,jobs_completed)
    navigate_to_inputs()
    input_product_code(product_code)
    units_of_measure() ### Checks UOM is set
    input_standard_quantity(standard_quantity)
    specify_process()
    input_date(date)
    #input_number_of_orders(number_of_orders)
    push_order()
    warnings_text = check_warnings()
    display_output(product_code,standard_quantity,date,time,number_of_orders,username,password,warnings_text,jobs_completed)

    
main(product_code,standard_quantity,date,time,number_of_orders,username,password,jobs_completed)

