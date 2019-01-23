#!/usr/bin/env python3

import sys
import json

try:
  import dns.resolver
except ImportError:
  print("ImportError for dnspython. To remedy: pip3 install dnspython", file=sys.stderr)
  sys.exit(3)

def dns_query(r_domain, r_type):
  "perform a DNS query and return a result matching the format used in the config file"
  r_type = r_type.upper()
  
  if r_type == "MX": out = {}
  else: out = []

  try:
    answers = dns.resolver.query(r_domain, r_type)
  except dns.resolver.NoAnswer:
    return None

  # Workaround for records with CNAME but no A/AAAA-record.
  # The DNS library I use resolves the CNAME in this instance,
  # and that's not the behaviour I want.
  if r_type in ('A', 'AAAA'):
    for answer in answers.response.answer:
      if " IN CNAME " in repr(answer):
        return None

  for rdata in answers:
    if r_type == "MX":
      if str(rdata.preference) in out.keys():
        out[str(rdata.preference)].append(rdata.exchange.to_text())
      else:
        out[str(rdata.preference)] = [rdata.exchange.to_text()]
    else:
      for rdata in answers:
        if rdata.to_text() not in out:
          out = sorted(out + [rdata.to_text()])

  if not out: return None
  return out


def find_mismatch(domain, expected):
  discrepancy = []
  for (record_type, record_data) in expected.items():
    if record_type.upper() in ('A', 'AAAA', 'TXT') and record_data:
      record_data = sorted(record_data)

    actual_data = dns_query(domain, record_type)
    if (actual_data != record_data):
      discrepancy.append("%s mismatch for %s. Expected: %s Actual: %s" % (domain, record_type, record_data, actual_data))
  
  return discrepancy
  

def main(config):
  discrepancies = []
  for domain in config.keys():
    expected = config[domain]
    discrepancies += find_mismatch(domain, expected)

  if discrepancies:
    print("CRITICAL - %s" % " AND ".join(discrepancies))
    sys.exit(2)

  # Clean nagios exit
  print("OK - %d domains checked" % len(config.keys()))
  sys.exit(0)

if __name__ == "__main__":
  try:
    config = json.load(open(sys.argv[1]))
  except IndexError:
    print("Syntax: %s configfile.json" % sys.argv[0])
    sys.exit(3)
  except json.decoder.JSONDecodeError as err:
    print("Malformed json in '%s': %s" % (sys.argv[1], err))
    sys.exit(3)

  main(config)

