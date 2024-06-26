#!/usr/bin/env python3
import base64
import codecs
import json
import subprocess
import time

from poshc2.client.reporting.ReportColumns import ReportColumns
from poshc2.client.reporting.ReportKeys import ReportKeys
from poshc2.server.Config import ReportsDirectory, ReportingDirectory, ImagesDirectory, PayloadCommsHost, DatabaseType
from poshc2.server.ImplantType import ImplantType
from poshc2.server.database.Model import Implant
from poshc2.server.database.Helpers import select_all, get_html_report_data


def generate_html_table(table):
    base = codecs.open(f"{ReportingDirectory}HTML_Template.html", 'r', 'utf-8').read()
    report_logo = open(f"{ImagesDirectory}ReportLogo.png", "rb")
    report_logo = str(base64.b64encode(report_logo.read()).decode('utf-8'))
    posh_logo = open(f"{ImagesDirectory}PoshC2Logo.png", "rb")
    posh_logo = str(base64.b64encode(posh_logo.read()).decode('utf-8'))
    columns = ReportColumns[table.__tablename__].value
    data = get_table_data(table)
    base = base.replace('__TITLE__', table.__tablename__)
    base = base.replace('__TABLECOLUMNS__', columns)
    base = base.replace('__TABLEDATA__', data)
    base = base.replace('__REPORTLOGO__', report_logo)
    base = base.replace('__POSHLOGO__', posh_logo)
    report_name = f"{ReportsDirectory}{table.__tablename__}.html"
    output_file = open(report_name, 'w')
    output_file.write(base)
    output_file.close()
    print(f"    {report_name}")


def get_table_data(table):
    frame = get_html_report_data(table)

    if frame is None or frame == []:
        return "[]"

    keys = frame[0].keys()
    output = []

    for row in frame:
        rowObj = {}

        for key in keys:
            rowObj[key] = str(row[key]).replace("</script>", "<\/script>")

        output.append(rowObj)

    return json.dumps(output)


# TODO test with postgre
"""
def table_data_postgres(frame, table_name):
    keys = ReportKeys[table_name].value
    output = []
    for row in frame:
        rowObj = {}
        for idx, key in enumerate(keys):
            rowObj[key] = str(row[idx]).replace("</script>", "<\/script>")
        output.append(rowObj)
    return json.dumps(output)


def table_data_sqlite(frame):
    keys = frame[0].keys()
    output = []
    for row in frame:
        rowObj = {}
        for key in keys:
            rowObj[key] = str(row[key]).replace("</script>", "<\/script>")
        output.append(rowObj)
    return json.dumps(output)
"""


def graphviz():
    GV = f"""
digraph "PoshC2" {{

  subgraph proxy {{
      node [color=white, fontcolor=red, fontsize=15, shapefile="{ImagesDirectory}/firewall.png"];
      "POSHSERVER";
  }}

  subgraph implant {{
      node [color=white, fontcolor=white, fontsize=15, shapefile="{ImagesDirectory}/implant.png"];
      IMPLANTHOSTS
  }}

  subgraph daisy {{
      node [color=white, fontcolor=white, fontsize=15, shapefile="{ImagesDirectory}/implant.png"];
      DAISYHOSTS
  }}

}}
  """

    ServerTAG = "\\n\\n\\n\\n\\n\\n\\n\\n\\n\\nPoshC2 Server\\n%s" % PayloadCommsHost.replace("\"", "")
    GV = GV.replace("POSHSERVER", ServerTAG)

    implants = select_all(Implant)
    hosts = ""
    daisyhosts = ""

    for implant in implants:
        implant_type = ImplantType.get(implant.type)
        
        if not implant_type.is_daisy_implant():
            if implant.hostname not in hosts:
                domain = implant.domain.replace("\\", "\\\\")
                hosts += f"\"{ServerTAG}\" -> \"{domain} \\n {implant.hostname}\\n\\n\\n\\n \"; \n"
        else:
            domain = implant.domain.replace("\\", "\\\\")

            if "\"%s\\n\\n\\n\\n \" -> \"%s \\n %s\\n\\n\\n\\n \"; \n" % (
                    implant_type.replace('\x00', '').replace("\\", "\\\\").replace('@', ' \\n '), domain, implant.hostname) not in daisyhosts:
                daisyhosts += "\"%s\\n\\n\\n\\n \" -> \"%s \\n %s\\n\\n\\n\\n \"; \n" % (
                    implant_type.replace('\x00', '').replace("\\", "\\\\").replace('@', ' \\n '), domain, implant.hostname)

    GV = GV.replace("DAISYHOSTS", daisyhosts)
    GV = GV.replace("IMPLANTHOSTS", hosts)
    output_file = open(f"{ReportsDirectory}PoshC2.dot", 'w')
    output_file.write(f"{GV}")
    output_file.close()
    subprocess.check_output(f"dot -T png -o {ReportsDirectory}PoshC2.png {ReportsDirectory}PoshC2.dot", shell=True)
    print("")
    print("GraphViz Generated PoshC2.png")
    print("")
    time.sleep(1)
