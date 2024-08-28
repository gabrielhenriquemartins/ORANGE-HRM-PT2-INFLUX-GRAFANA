import requests
import json
import sys
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient, Point, WritePrecision, DeleteApi
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException
from datetime import datetime, timezone

# Configuração
jira_domain = "your-domain"
xray_url = "https://xray.cloud.getxray.app/"

email = "your-email"
api_token = "your-token"

client_id = "your-cliend-id"
client_secret = "your-client-secret"

max_results = 50

days_before_test_outdated = 8

#InfluxDB configuration
url = "http://localhost:8086"
token = "3e6a5f96b27fc69d5b5005f62ef57009d8b0e96a2fb1f06a2ac1a3d3d79b9d5a"
org = "orange"
my_bucket = "jira"
retention_policy = "30d"

#Measurements
measurement_1 = "total_number_of_tests"
measurement_2 = "old_updated_tests"
measurement_3 = "tests_empty_body"
measurement_4 = "automated_tests"
measurement_5 = "manual_tests"
measurement_6 = "create_tests"
measurement_7 = "rectly_updated"
measurement_8 = "not_exec_not_updt"
measurement_9 = "run_ratio"

timestamp = datetime.today().isoformat()


# ---------------------------------------------- #
#            Get values from command line        #
# ---------------------------------------------- #
def get_values_in_command_line():
    global jira_domain, email, api_token, client_id, client_secret
    if len(sys.argv) == 6:
        jira_domain = sys.argv[1]
        print(f'Jira Domain: {jira_domain}')
        email = sys.argv[2]
        print(f'Email: {email}')
        api_token = sys.argv[3]
        print(f'Jira Token: {api_token}')
        client_id = sys.argv[4]
        print(f'Xray, Client ID: {client_id}')
        client_secret = sys.argv[5]
        print(f'Xray, Client Secret: {client_secret}')
    else:
        print("Not enough arguments provided.")

# ---------------------------------------------- #
#          Delete and Create Bucket              #
# ---------------------------------------------- #
def new_bucket():
    create_bucket = True
    client = InfluxDBClient(url=url, token=token, org=org)

    # Check if the bucket already exists
    buckets_api = client.buckets_api()
    existing_buckets = buckets_api.find_buckets().buckets
    for bucket in existing_buckets:
        print(bucket.name)
        if bucket.name == my_bucket:
            print(f"Bucket already exists.")
            create_bucket = False
            break
    if create_bucket:
        client.buckets_api().create_bucket(bucket_name=my_bucket, retention_rules=[{"everySeconds": 86400 * 30}])

# ---------------------------------------------- #
#          Write data into influx DB             #
# ---------------------------------------------- #
def write(measurement, value):
    #InfluxDB client
    client = InfluxDBClient(url=url, token=token, org=org)

    #Create a Point with specified timestamp and value
    point = Point(measurement) \
        .time(timestamp, WritePrecision.MS) \
        .field("value", value)

    #Write point to InfluxDB
    try:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=my_bucket, record=point)

        print(f"Successfully sent value {value} to InfluxDB")

    except ApiException as e:
        print(f"Error during write operation: ({e.status})")
        print(f"Reason: {e.reason}")
        if hasattr(e, 'body'):
            print(f"HTTP response body: {e.body}")

    #Close connection
    finally:
        client.close()

# ---------------------------------------------- #
#     Delete all values from a measurement       #
# ---------------------------------------------- #
def drop_measurement(measurement_name):
    #InfluxDB client
    client = InfluxDBClient(url=url, token=token, org=org)

    try:
        #Initialize DeleteApi
        delete_api = DeleteApi(client)
        time = datetime.now(timezone.utc)

        #Delete all the values in measurement
        delete_api.delete('1970-01-01T00:00:00Z', time, org=org, bucket=my_bucket, predicate=f'_measurement="{measurement_name}"')

        print(f"Measurement '{measurement_name}' dropped successfully.")

    except Exception as e:
        print(f"Error dropping measurement '{measurement_name}': {e}")

    #Close connection
    finally:
        client.close()

#######################################
### Single request to get all tests ###
#######################################
def get_all_tests(issuetype = "Test", number_of_days=None):
    url = f"{jira_domain}/rest/api/2/search"
    auth = HTTPBasicAuth(email, api_token)
    jql_query = f'project = OTS AND issuetype = "{issuetype}"'
    headers = {
        "Accept": "application/json"
    }

    params = {
        "jql": jql_query,
        "startAt": 0,
        "maxResults": max_results,
        "fields": "key,summary,description,updated,created"
        }

    test_issues = []

    if number_of_days:
        today = datetime.now().date()
        updated_date = today - timedelta(days=int(number_of_days))

    while True:
        response = requests.get(url, headers=headers, auth=auth, params=params)

        if response.status_code == 200:
            data = response.json()
            issues = data.get("issues", [])
            
            if not issues:
                return  test_issues

            for issue in issues:
                test_info = {
                    "key": issue.get("key"),
                    "summary": issue.get("fields", {}).get("summary", ""),
                    "description": issue.get("fields", {}).get("description", ""),
                    "updated": issue.get("fields", {}).get("updated", "")[0:10],
                    "created": issue.get("fields", {}).get("created", "")[0:10]
                }
                
                test_updated = datetime.strptime(test_info['updated'][0:10], "%Y-%m-%d").date()
                if number_of_days:
                    if test_updated > updated_date:
                        test_issues.append(test_info)
                else:
                    test_issues.append(test_info)

            params["startAt"] += max_results
        else:
            print(f"Jira is not responding!!!")
            break

#######################################
## Get Old Tests Updated - Last Week ##
#######################################
def updated_tests(tests):
    print('\n----------------------------------------')
    print('------------- TEST UPDATED -------------')
    updated = 0
    for test in tests:
        today = datetime.now().date()
        last_week = today - timedelta(days=7)
        date_before_test_outdated = today - timedelta(days=days_before_test_outdated)
        test_created = datetime.strptime(test['created'][0:10], "%Y-%m-%d").date()
        test_updated = datetime.strptime(test['updated'][0:10], "%Y-%m-%d").date()
        if date_before_test_outdated > test_created:
            if last_week < test_updated:
                updated = updated + 1
                print(f'The test: {test['key']} -> {test['summary']} was created in {test['created']} and was updated in {test['updated']}')
    print('----------------------------------------')
    print(f'--- TEST UPDATED -> DONE <- {updated} UPDATE ---')
    print('----------------------------------------')
    return updated

#######################################
######## TOTAL NUMBER OF TESTS ########
#######################################
def total_of_tests(tests):
    total = len(tests)
    print('\n----------------------------------------')
    print(f'--- TOTAL TESTS -> DONE <- {total} TESTS ---')
    print('----------------------------------------')
    return total

#######################################
######## TESTS WITH EMPTY BODY ########
#######################################
def tests_with_empty_body(tests):
    print('\n-----------------------------------------------')
    print('------------- TESTS W/ EMPTY BODY -------------')
    empty_body = 0
    for test in tests:
        if test['description'] == None:
            print(f'The test: {test['key']} -> {test['summary']} => Does not contains a description!')
            empty_body = empty_body + 1
    print('-----------------------------------------------')
    print(f'---- TESTS W EMPTY BODY -> DONE <- {empty_body} EMPTY ----')
    print('-----------------------------------------------')
    return empty_body
    
#######################################
###### Number of automated Tests ######
#######################################
def number_of_automated_tests(tests):
    automated = 0
    for test in tests:
        if "CY" in test['summary'] or "Robot" in test['summary']:
            automated = automated + 1
    print('\n-----------------------------------------------')
    print(f'-- AUTOMATED TESTS -> DONE <- {automated} AUTOMATED ---')
    print('-----------------------------------------------')
    return automated

#######################################
####### Number of manual tests ########
#######################################
def number_of_manual_tests(tests):
    manual = 0
    for test in tests:
        if "MANUAL" in test['summary']:
            manual = manual + 1
    print('\n-----------------------------------------------')
    print(f'------ MANUAL TESTS -> DONE <- {manual} MANUAL -------')
    print('-----------------------------------------------')
    return manual


#######################################
### Number created tests last week ####
#######################################
def number_of_created_tests(tests):
    print('\n----------------------------------------')
    print('------- CREATED TESTS - LAST WEEK ------')
    created = 0
    for test in tests:
        today = datetime.now().date()
        last_week = today - timedelta(days=7)
        test_created = datetime.strptime(test['created'][0:10], "%Y-%m-%d").date()
        if test_created > last_week:
            created = created + 1
            print(f'New Test: {test['key']} -> {test['summary']} created in {test_created}')
    print('\n----------------------------------------')
    print(f'-- TESTS CREATED -> DONE <- {created} CREATED --')
    print('----------------------------------------')
    return created

#######################################
### Number updated tests last week ####
#######################################
def number_of_updated_tests(tests):
    print('\n----------------------------------------')
    print('------- UPDATED TESTS - LAST WEEK ------')
    updated = 0
    for test in tests:
        today = datetime.now().date()
        last_week = today - timedelta(days=7)
        test_updated = datetime.strptime(test['updated'][0:10], "%Y-%m-%d").date()
        if test_updated > last_week:
            updated = updated + 1
            print(f'Update Test: {test['key']} -> {test['summary']} updated in {test_updated}')
    print('----------------------------------------')
    print(f'-- TESTS UPDATED -> DONE <- {updated} UPDATED --')
    print('----------------------------------------')
    return updated

#######################################
######## XRAY AUTHENTICATION ##########
#######################################
def authenticate(client_id, client_secret):
    url = "https://xray.cloud.getxray.app/api/v2/authenticate"
    payload = json.dumps({
        "client_id": client_id,
        "client_secret": client_secret
    })
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        print("Authentication successful")
        return response.text.strip('"')
    else:
        raise Exception(f"Authentication failed!")

#######################################
######## GET TEST CASE KEYS ###########
#######################################
def extract_test_case(result):
    test_case_keys = set()
    if 'data' in result and 'getTestExecutions' in result['data']:
        test_executions = result['data']['getTestExecutions']['results']
        for execution in test_executions:
            tests = execution['tests']['results']
            for test in tests:
                key = test['jira']['key']
                test_case_keys.add(key)
    return list(test_case_keys)

#######################################
##### GET TEST CASE IN TEST EXEC ######
#######################################
def get_tests_in_test_executions(api_token, test_executions):
    single_array_all_execution = []
    multi_array_all_execution = []
    for test_execution in test_executions:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_token}'
        }
        query = {
            "query": f'''
            {{
                getTestExecutions(jql: "key = {test_execution['key']}", limit: 100) {{
                    results {{
                        tests(limit: 100) {{
                            results {{
                                jira(fields: ["key"])
                            }}
                        }}
                    }}
                }}
            }}'''
        }
        xray_graphql_url = 'https://xray.cloud.getxray.app/api/v2/graphql'
        response = requests.post(xray_graphql_url, headers=headers, json=query)
        response.raise_for_status()
        test_cases = extract_test_case(response.json())
        if test_cases not in multi_array_all_execution:
            multi_array_all_execution.append(test_cases)
    single_array_all_execution = [item for array in multi_array_all_execution for item in array]
    single_array_all_execution = list(set(single_array_all_execution))
    return single_array_all_execution
    
#######################################
##### GET TEST CASE IN TEST EXEC ######
#######################################
def compare_dict_and_array(first, second, should_print=True):
    result = [d for d in first if d['key'] not in second]
    
    for test in result:
        if should_print:
            print(f"The test {test['key']} - {test['summary']} => Is not updated and was not executed ...")
    return len(result)

##############################################
# GET ALL NOT EXECUTED AND NOT UPDATED TESTS #
##############################################
def not_executed_not_updated(token, all_tests, days, should_print=True):
    if should_print:
        print('\n-----------------------------------------')
        print('------------- TEST OUTDATED -------------')
    all_test_executions = get_all_tests("Test Execution", int(days))
    tests = get_tests_in_test_executions(token, all_test_executions)
    results = compare_dict_and_array(all_tests, tests, should_print)
    if should_print:
        print('-----------------------------------------')
        print(f'--- TESTS OUTDATED -> DONE <- {results} TESTS ---')
        print('-----------------------------------------')
    return results

##############################################
########### RUN RATIO - LAST WEEK ############
##############################################
def automation_executed_last_week(token, all_tests, automated = None):
    if (automated == None):
        automated = number_of_automated_tests(all_tests)
    result = not_executed_not_updated(token, all_tests, "7", False)
    percentage_run = round(100*(automated - result)/automated, 2)
    print('\n-----------------------------------------')
    print(f'-- TEST AUTOMATED RUN -> DONE <- {percentage_run}% -')
    print('-----------------------------------------')
    return percentage_run

############################################################################
############################################################################
############################################################################
#######################      SCRIPT       ##################################
############################################################################
############################################################################
############################################################################

get_values_in_command_line()
new_bucket()
xray_token = authenticate(client_id, client_secret)
all_tests = get_all_tests()
number_of_tests = total_of_tests(all_tests)
write(measurement_1, number_of_tests)

updated = updated_tests(all_tests)
write(measurement_2, updated)

empty_body = tests_with_empty_body(all_tests)
write(measurement_3, empty_body)

automated = number_of_automated_tests(all_tests)
write(measurement_4, automated)

manual = number_of_manual_tests(all_tests)
write(measurement_5, manual)

created = number_of_created_tests(all_tests)
write(measurement_6, created)

number_of_updated = number_of_updated_tests(all_tests)
write(measurement_7, number_of_updated)

not_executed = not_executed_not_updated(xray_token, all_tests, "2")
write(measurement_8, not_executed)

run_ratio = automation_executed_last_week(xray_token, all_tests, automated)
write(measurement_9, run_ratio)