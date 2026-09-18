<!-- Initial product requirements for the CSV usage reporting API. -->
TechStack Python and FastAPI

to be deployed on digital ocean - we will use digital ocean's postgres DB

REST API that allows engineers to upload a csv with their request logs with headers request_id, service, status_code, latency_ms, tokens_used. Each row will represent an API request

functional requirements
User can upload csv file
Csv file is validated
Report is created from csv file
User can list all previous reports and an individual report

Plan:
Connect to digital ocean postgres db and deploy
Create basic tests as a baseline for our implementation

