import requests
import csv
from bs4 import BeautifulSoup

URL = "https://www.linkedin.com/pulse/top-10-job-portals-india-freshers-experienced-professionals-gedqc"
headers = {"User-Agent": "Mozilla/5.0"}

response = requests.get(URL, headers=headers)
print(response.status_code)
print(len(response.text))

soup = BeautifulSoup(response.text, 'html.parser')
job_cards = soup.select('.srp-jobtuple-wrapper')

results = []

for card in job_cards:
    title_elem = card.select_one('a.title')
    if not title_elem:
        continue
    title = title_elem.text.strip()
    company_elem = card.select_one('a.comp-name')
    subTitle_elem = card.select_one('.subTitle')
    company = company_elem.text.strip() if company_elem else (subTitle_elem.text.strip() if subTitle_elem else '')
    location_elem = card.select_one('.locWdth')
    location = location_elem.text.strip() if location_elem else ''
    link = title_elem['href'] if title_elem else ''
    job = {
        'title': title,
        'company': company,
        'location': location,
        'link': link
    }
    print(job)
    results.append(job)

# Save to CSV
with open('jobs.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['title', 'company', 'location', 'link']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

print(f"Rows written to jobs.csv: {len(results)}")

# Save to TXT
with open('scrape_results.txt', 'w', encoding='utf-8') as f:
    f.write(f"Status Code: {response.status_code}\n")
    f.write(f"Response Length: {len(response.text)}\n")
    f.write(f"Total Jobs Found: {len(results)}\n\n")
    for job in results:
        f.write(str(job) + '\n')

print(f"\nResults saved to scrape_results.txt ({len(results)} jobs found)")

# Build HTML rows
if results:
    rows = ""
    for job in results:
        rows += f"""
        <tr>
            <td><a href="{job['link']}" target="_blank">{job['title']}</a></td>
            <td>{job['company']}</td>
            <td>{job['location']}</td>
        </tr>"""
else:
    rows = "<tr><td colspan='3'>No job listings found on this page.</td></tr>"

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scraped Job Results</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 0 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #333;
        }}
        .meta {{
            background: #fff;
            padding: 10px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #555;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #fff;
            border-radius: 6px;
            overflow: hidden;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        }}
        th {{
            background: #0073b1;
            color: white;
            padding: 12px 16px;
            text-align: left;
        }}
        td {{
            padding: 10px 16px;
            border-bottom: 1px solid #eee;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        a {{
            color: #0073b1;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <h1>Scraped Job Results</h1>
    <div class="meta">
        <strong>Source URL:</strong> {URL}<br>
        <strong>Status Code:</strong> {response.status_code}<br>
        <strong>Total Jobs Found:</strong> {len(results)}
    </div>
    <table>
        <thead>
            <tr>
                <th>Job Title</th>
                <th>Company</th>
                <th>Location</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</body>
</html>
"""

with open('scrape_results.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Results also saved to scrape_results.html")
