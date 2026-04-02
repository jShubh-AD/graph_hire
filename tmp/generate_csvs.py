import json
import csv

def generate_csvs():
    with open("jobs_data.json", "r") as f:
        data = json.load(f)
    
    with open("tmp/posted_by.csv", "w", newline="") as f:
        writer = csv.writer(f)
        for edge in data["posted_by"]:
            writer.writerow([edge["source_id"], edge["target_id"]])
            
    with open("tmp/requires_skill.csv", "w", newline="") as f:
        writer = csv.writer(f)
        for edge in data["requires_skill"]:
            writer.writerow([edge["source_id"], edge["target_id"], edge["importance"]])

    print("CSVs generated successfully in tmp/")

if __name__ == "__main__":
    generate_csvs()
