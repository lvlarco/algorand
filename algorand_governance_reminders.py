import requests
import json
from datetime import datetime, timedelta


def request_governance_data(active=False):
    """Sends GET request to pull information about Algorand governance periods
    :param active: bool.    Request to active period or all periods
    """
    gov_url = 'https://governance.algorand.foundation/api/periods/'
    if active:
        data = requests.get('{}{}'.format(gov_url, 'active'))
    else:
        data = requests.get(gov_url)
    return data.json()


def read_json(file):
    f = open(file)
    return json.load(f)


def write_json(file, feed):
    with open(file, mode='w') as f:
        json.dump(feed, f, indent=2)


def format_timestamp(str_timestamp):
    try:
        return datetime.strptime(str_timestamp, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        print('{} is not a datetime type'.format(str_timestamp))
        return str_timestamp


def format_timestamps(list_timestamp):
    return [format_timestamp(t) for t in list_timestamp]


def get_current_period(str_slug):
    """Parses the data slug and extracts the current period"""
    try:
        return int(str_slug[-1])
    except ValueError:
        print('{}, datatype {} cannot be converted to an integer'.format(str_slug, type(str_slug)))


def send_ifttt_request(event, key, json_data):
    maker_url = 'https://maker.ifttt.com/trigger/{}/with/key/{}'.format(event, key)
    print('Sending IFTTT request for event {}'.format(event))
    requests.post(maker_url, data=json_data)


def create_payload(val1, val2, val3):
    """Writes json payload with information to provide to IFTTT"""
    return {"value1": val1, "value2": val2, "value3": val3}


def get_new_period_timeline(data):
    """Extracts start and end dates for the new period
    :param data: dict.  Period data in dictionary format"""
    strf_format = '%b %d'
    newest_start = max(format_timestamp(per.get('start_datetime')) for per in data)
    newest_registration_end = max(format_timestamp(per.get('registration_end_datetime')) for per in data)
    return newest_start.strftime(strf_format), newest_registration_end.strftime(strf_format)


if __name__ == '__main__':
    current_time = datetime.now()
    api_key = 'gQcp1_HM80LpLpKQ2VHBPRISAWGGfz0sJxAprH-KWmg'
    json_file = 'governance_snapshot.json'
    snapshot_data = read_json(json_file)

    # Voting sessions/active data
    active_data = request_governance_data(active=True)
    current_period = get_current_period(active_data.get('slug'))
    for session in active_data.get('voting_sessions'):
        session_start = format_timestamp(session.get('voting_start_datetime'))
        session_end = format_timestamp(session.get('voting_end_datetime'))
        if timedelta(minutes=1) < (current_time - session_start) <= timedelta(days=5):
            payload = create_payload(current_period, session_start, session_end)
            send_ifttt_request('reminder_algo_vote', api_key, payload)

    # Period data
    period_data = request_governance_data(active=False)
    period_count = period_data.get('count')
    if period_count > snapshot_data.get('current_period'):
        new_period_start, new_period_end = get_new_period_timeline(period_data.get('results'))
        payload = create_payload(period_count, new_period_start, new_period_end)
        send_ifttt_request('new_algo_gov_period', api_key, payload)
    for period in period_data.get('results'):
        period_start = format_timestamp(period.get('start_datetime'))
        if abs(period_start - current_time) <= timedelta(days=5):
            new_period_start, new_period_end = get_new_period_timeline(period_data.get('results'))
            payload = create_payload(period_count, new_period_start, new_period_end)
            send_ifttt_request('reminder_algo_signup', api_key, payload)

    snapshot = {"period_count": period_count,
                "current_period": current_period,
                "snapshot_timestamp": current_time.strftime('%Y-%m-%d %H:%M')}
    write_json(json_file, snapshot)
