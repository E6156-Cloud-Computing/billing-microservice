# billing-microservice

This billing system contains 2 docker containers

## MongoDB container
Using official mongodb docker image

## Application Container
Python + Flask

## Usage
Do `docker-compose up --build` to launch

## Test APIs
I choose to use Postman for API testing
This is how ChatGPT instruct me to use Postman for API testing:

1. **Install Postman**: If you don't already have Postman, you can download and install it from [the Postman website](https://www.postman.com/downloads/).
2. **Create a New Request**:
    - Open Postman.
    - Click on the "New" button and select "Request".
    - Give your request a name and optionally create a collection to organize your requests.
3. **Set Up and Send Requests**:
    - Enter your API URL in the request URL field. For example, `http://localhost:5000/api/billing/transaction/` for fetching all transactions.
    - Select the appropriate HTTP method (GET, POST, PUT, DELETE) based on the API endpoint you are testing.
    - For POST and PUT requests, you may need to add request body data. Go to the "Body" tab, select "raw", and choose "JSON" from the dropdown. Enter your JSON payload here.
    - Click "Send" to make the request and view the response in the lower section of the Postman window.
4. **Analyze the Response**:
    - After sending the request, Postman will display the server's response, including status code, headers, and body.
    - Review the response to ensure that it matches your expectations.