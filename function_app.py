import logging
import azure.functions as func
import requests
from bs4 import BeautifulSoup
import re
from twilio.rest import Client
import time
import os

app = func.FunctionApp()

@app.timer_trigger(schedule="0 0 * * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False)
def timer_trig(myTimer: func.TimerRequest) -> None:
    def get_car_listings():
        url = "https://qatarsale.com/en/products/cars_for_sale?sortBy=AuctionStartTime_desc&page=1"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        allcarsdetails = soup.find("div", class_=re.compile(r"ng-tns-c\d{3}-3 product-list classic ng-star-inserted"))

        # Check if there are car details available
        if allcarsdetails:
            car_listings = []
            details = allcarsdetails.find_all("qs-product-card-v2", class_=re.compile(r"ng-tns-c\d{3}-\d{2} ng-tns-c\d{3}-3 ng-star-inserted"))

            # Extract details for each car listing
            for detail in details:
                car = extract_details(detail)
                car_listings.append(car)

            return car_listings
        return []

        # Function to extract details of a car
    def extract_details(text):
        car_listing = []

        # Find car visual elements and details
        car_visual = text.find("a", class_="img-loading ng-star-inserted") if text.find("a", class_="img-loading ng-star-inserted") else None
        car_link = car_visual.get("href") if car_visual else None
        car_img = car_visual.find("img", class_="prod-img").get("src") if car_visual else None
        carinfo = text.find("div", class_="product-definitions") if text.find("div", class_="product-definitions") else None
        carmakemodel = text.find("div", class_="product-details") if text.find("div", class_="product-details") else None
        carprice = text.find("div", class_="product-controls").find("p", class_=re.compile(r"p1 ng-tns-c\d{3}-\d{2}")).get_text() if text.find("div", class_="product-controls").find("p", class_=re.compile(r"p1 ng-tns-c\d{3}-\d{2}")) else None
        
        make = carmakemodel.find("p", class_="p3 ng-star-inserted").get_text() if carmakemodel.find("p", class_="p3 ng-star-inserted") else None
        model1 = carmakemodel.find("p", class_="p5 ng-star-inserted").get_text() if carmakemodel.find("p", class_="p5 ng-star-inserted") else None
        submodel = carmakemodel.find("p", class_="p5 sub-header ng-star-inserted").get_text() if carmakemodel.find("p", class_="p5 sub-header ng-star-inserted") else None
        type = carmakemodel.find("p", class_=re.compile(r"p5 ng-tns-c\d{3}-\d{2}")).get_text() if carmakemodel.find("p", class_=re.compile(r"p5 ng-tns-c\d{3}-\d{2}")) else None
        
        year = carinfo.find("div", style="order:0;").find("span", class_="def-value").get_text() if carinfo.find("div", style="order:0;").find("span", class_="def-value") else None
        geartype = carinfo.find("div", style="order:1;").find("span", class_="def-value").get_text() if carinfo.find("div", style="order:1;").find("span", class_="def-value") else None
        cylinders = carinfo.find("div", style="order:2;").find("span", class_="def-value").get_text() if carinfo.find("div", style="order:2;").find("span", class_="def-value") else None
        mileage = carinfo.find("div", style="order:3;").find("span", class_="def-value").get_text() if carinfo.find("div", style="order:3;").find("span", class_="def-value") else None
        car_listing = [make, model1, submodel, carprice, type, year, geartype, cylinders, mileage, car_link, car_img]
        return car_listing
    def send_message(car_details):
        webhook_url = os.getenv("WEBHOOK_URL")
        data = {
            "content": (
                f"New car listing:\n"
                f"Make: {car_details[0]}\n"
                f"Model: {car_details[1]}\n"
                f"Submodel: {car_details[2]}\n"
                f"Price: {car_details[3]} QAR\n"
                f"Type: {car_details[4]}\n"
                f"Year: {car_details[5]}\n"
                f"Gear Type: {car_details[6]}\n"
                f"Cylinders: {car_details[7]}\n"
                f"Mileage: {car_details[8]}\n"
                f"Link: <{car_details[9]}>\n"
                f"Image: {car_details[10]}"
            )
        }
        requests.post(webhook_url, json=data)
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        client = Client(account_sid, auth_token)
        
        client.messages.create(
            body=(
                f"New car listing:\n"
                f"Make: {car_details[0]}\n"
                f"Model: {car_details[1]}\n"
                f"Submodel: {car_details[2]}\n"
                f"Price: {car_details[3]} QAR\n"
                f"Type: {car_details[4]}\n"
                f"Year: {car_details[5]}\n"
                f"Gear Type: {car_details[6]}\n"
                f"Cylinders: {car_details[7]}\n"
                f"Mileage: {car_details[8]}\n"
                f"Link: {car_details[9]}"
            ),
            from_='whatsapp:+447311729387',
            to='whatsapp:+97455741660',
        )
    def check(current, previous):
        new_listings = [car for car in current if car not in previous]
        logging.info(f"New listings: {len(new_listings)}\n")
        
        if new_listings:
            for car in new_listings:
                if car not in previous:
                    logging.info(f"Sending message for car: {car[0]} {car[1]} {car[2]}")
                    send_message(car)
                    time.sleep(1)
        
        return current
    if myTimer.past_due:
        logging.info('The timer is past due!')
    logging.info("Fetching current car listings...")
    car_listings = get_car_listings()
    previous = []
    try:
        with open("/tmp/cars.txt", "r") as file:
            for line in file:
                previous.append(eval(line.strip()))
    except FileNotFoundError:
        with open("/tmp/cars.txt", "w") as f:
            f.write("")
    if car_listings == previous:
        logging.info("No new cars")
    else:
        current = check(car_listings, previous)
        with open("/tmp/cars.txt", "w") as f:
            for car in current:
                f.write(f"{car}\n")
    logging.info("Exiting main function")
    logging.info('Python timer trigger function executed.')
    logging.info("")
