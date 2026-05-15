import csv
from datetime import datetime

txt_file_path = 'parameter_changes.txt'
csv_file_path = 'flowdoscheck_stats_2024-01-19_202703.csv'
new_csv_file_path = 'TimeSeriesData_DDoS.csv'

def read_txt_file(txt_file_path):
    txt_data = []
    with open(txt_file_path, 'r') as file:
        for line in file:
            parts = line.split(',')
            time_str = parts[0].split(': ')[1]
            time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            txt_data.append((time, parts[1:]))
    return txt_data

def read_csv_file(csv_file_path):
    csv_data = []
    with open(csv_file_path, 'r') as file:
        csv_reader = csv.reader(file)
        headers = next(csv_reader)
        for row in csv_reader:
            time_str = row[0]
            time = datetime.strptime(time_str, '%Y/%m/%d %H:%M:%S %Z')
            csv_data.append((time, row[1:]))
    return headers, csv_data

def find_and_merge(txt_data, csv_data, headers):
    merged_data = []
    txt_index = 0
    for csv_time, csv_row in csv_data:
        while txt_index < len(txt_data) and txt_data[txt_index][0] <= csv_time:
            txt_index += 1
        if txt_index > 0:
            merged_row = [csv_time] + txt_data[txt_index - 1][1] + csv_row
            merged_data.append(merged_row)
    return merged_data

def write_merged_csv(new_csv_file_path, headers, merged_data):
    with open(new_csv_file_path, 'w', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(['Date', 'Port', 'Protocol', 'packet_size', 'attack_type'] + headers[1:])
        for row in merged_data:
            csv_writer.writerow(row)

txt_data = read_txt_file(txt_file_path)
headers, csv_data = read_csv_file(csv_file_path)
merged_data = find_and_merge(txt_data, csv_data, headers)
write_merged_csv(new_csv_file_path, headers, merged_data)

