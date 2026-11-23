import unittest
import socket
from unittest.mock import patch
from jarvis_core.web_navigation import validate_url,browse,research_urls,WebNavigationError

def public_dns(host,port,type=None):
 return [(socket.AF_INET,socket.SOCK_STREAM,6,"",("93.184.216.34",443))]
def private_dns(host,port,type=None):
 return [(socket.AF_INET,socket.SOCK_STREAM,6,"",("127.0.0.1",443))]
class WebNavigationTests(unittest.TestCase):
 def test_https_public(self):
  self.assertEqual(validate_url("https://example.com/a",public_dns),"https://example.com/a")
 def test_reject_private_hosts_and_ip(self):
  for url in ("http://example.com","https://localhost","https://127.0.0.1",
              "https://example.com:8443","https://user:pass@example.com"):
   with self.assertRaises(WebNavigationError):validate_url(url,private_dns)
 def test_extract_html_and_ignore_scripts(self):
  with patch("jarvis_core.web_navigation.socket.getaddrinfo",side_effect=public_dns):
   result=browse("https://example.com",lambda url:("<h1>Informe</h1><script>secret</script><p>Dato público</p>","text/html"))
  self.assertIn("Dato público",result["excerpt"])
  self.assertNotIn("secret",result["excerpt"])
  self.assertFalse(result["verified"])
 def test_multi_source(self):
  with patch("jarvis_core.web_navigation.socket.getaddrinfo",side_effect=public_dns):
   result=research_urls(["https://example.com","https://example.org"],lambda url:("Texto de prueba","text/plain"))
  self.assertEqual(result["source_count"],2)
 def test_reject_empty(self):
  with self.assertRaises(WebNavigationError):research_urls([])
if __name__=="__main__":unittest.main()
