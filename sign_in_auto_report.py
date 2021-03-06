from selenium import webdriver
from time import sleep
import win32com.client as win32   
import datetime
import webbrowser
import os
import shutil

chrome_options = webdriver.ChromeOptions()
prefs = {"profile.default_content_setting_values.notifications" : 2}
chrome_options.add_experimental_option("prefs",prefs)
driver = webdriver.Chrome(chrome_options=chrome_options)

## Sign In details 
username = ""
password = ""

## Get todays date and do date stuff
today = datetime.date.today()
while today.weekday() != 0:
    today = today - datetime.timedelta(days=1)
def previous_week_range(date):
    start_date = date + datetime.timedelta(-date.weekday(), weeks=-1)
    end_date = date + datetime.timedelta(-date.weekday() - 1)
    return(start_date, end_date)

def convert_date(pulled_date):
    formatted_date = pulled_date.replace(",","")
    formatted_date = formatted_date.split()
    formatted_date[0] = str(datetime.date.today().year)
    datetime_object = datetime.datetime.strptime(formatted_date[1], "%b")
    month_number = datetime_object.month
    if month_number < 10:
        month_number = "0"+ str(month_number)
    formatted_date[1] = str(month_number)
    if int(formatted_date[2]) < 10:
        formatted_date[2] = "0" + formatted_date[2]
    formatted_date = "-".join(formatted_date)
    formatted_date = datetime.datetime.strptime(formatted_date,"%Y-%m-%d")
    return formatted_date

driver.get("https://my.signinapp.com/")
driver.find_element_by_css_selector("[aria-label=Email]").send_keys(username)
driver.find_element_by_css_selector("[aria-label=Password]").send_keys(password)
driver.find_element_by_css_selector("[role=button]").click()
sleep(2)
driver.find_element_by_xpath('//a[contains(@href,"/reports")]').click()
sleep(0.5)
driver.find_element_by_css_selector("[role=button]").click()
sleep(0.5)
driver.find_element_by_xpath('//span[contains(text(), "Export")]').click()
sleep(0.5)
driver.find_element_by_xpath('//span[contains(text(), "All")]').click()
sleep(0.5)
driver.find_element_by_xpath('//div[contains(text(), "NP Contractors")]').click()
sleep(0.5)
driver.find_element_by_xpath('//i[contains(text(), "event")]').click()
sleep(0.5)

pulled_date = driver.find_element_by_xpath('/html/body/div[5]/div/div[1]/div[2]/div/div').text

formatted_date = convert_date(pulled_date)  
start_date,end_date = previous_week_range(today)
month_long = formatted_date.strftime("%B")


if formatted_date.month > start_date.month:
    driver.find_element_by_xpath('//i[contains(text(),"chevron_left")]').click()
    sleep(0.5)

    
if formatted_date.day != start_date.day:
    day = str(start_date.strftime("%d"))
    driver.find_element_by_xpath("//span[@class='block'][contains(text(),"+day+")]").click()

driver.find_element_by_xpath('//*[@id="route-wrapper"]/div/div[2]/div[2]/div/div[2]/div[2]/label/div/div/div[1]').click()

sleep(0.5)
if formatted_date.month > end_date.month:
    driver.find_element_by_xpath('//i[contains(text(),"chevron_left")]').click()
    sleep(0.5)


if formatted_date.day != end_date.day:
    day = str(end_date.strftime("%d"))
    driver.find_element_by_xpath("//span[@class='block'][contains(text(),"+day+")]").click()

driver.find_element_by_xpath('//*[@id="route-wrapper"]/div/div[2]/div[2]/div/div[3]/div/div/div[2]/div/div[1]/div').click() ## Deselect Site
driver.find_element_by_xpath('//*[@id="route-wrapper"]/div/div[2]/div[2]/div/div[3]/div/div/div[3]/div/div[1]').click()     ## DeSelect Group
driver.find_element_by_xpath('//*[@id="route-wrapper"]/div/div[2]/div[2]/div/div[3]/div/div/div[9]/div/div[1]/div').click() ## Select Duration Hours
driver.find_element_by_xpath('/html/body/div[1]/div[1]/div/div/div[2]/div[2]/div/div[5]/div/div/div[1]/div/div[1]/div').click() ## Select Company
driver.find_element_by_xpath('//*[@id="route-wrapper"]/div/div[2]/div[2]/div/div[6]/button/span[2]/span/span').click() ## Export

sleep(2)
driver.quit()

file_name = str(start_date)+" " + str(end_date) +".csv"
old_file_name = ".csv"
sleep(0.5)
new_file_name = ""+file_name
os.rename(old_file_name,new_file_name)

outlook = win32.Dispatch('outlook.application')
mail = outlook.CreateItem(0)
mail.To = ""
mail.Subject = "Contract Hours Report"
mail.HtmlBody = "Please find attached contract hours report"
mail.Attachments.Add(new_file_name)
mail.send

shutil.move(""+file_name,"")





