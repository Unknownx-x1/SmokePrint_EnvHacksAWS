import boto3

session = boto3.Session(region_name='us-east-1')
cf = session.client('cloudformation')

try:
    res = cf.describe_stacks(StackName='smokeprint-web-stack')
    stack = res['Stacks'][0]
    print('StackStatus:', stack['StackStatus'])
    if 'Outputs' in stack:
        for o in stack['Outputs']:
            print(f"  {o['OutputKey']}: {o['OutputValue']}")
except Exception as e:
    print('Error:', e)
