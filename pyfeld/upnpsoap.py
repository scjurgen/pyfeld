from __future__ import unicode_literals

import urllib3


class UpnpSoap:
    @staticmethod
    def extractSingleTag(self, data, tag):
        startTag = "<%s" % tag
        endTag = "</%s>" % tag
        try:
            tmp = data.split(startTag)[1]
            index = tmp.find('>')
            if index != -1:
                index += 1
                return tmp[index:].split(endTag)[0].strip()
        except:
            pass
        return None

    @staticmethod
    def send(host_name, service_type, control_url, action_name, action_arguments):

        if '://' in control_url:
            urls = control_url.split('/', 3)
            if len(urls) < 4:
                control_url = '/'
            else:
                control_url = '/' + urls[3]

        request = 'POST %s HTTP/1.1\r\n' % control_url

        # Check if a port number was specified in the host name; default is port 80
        if ':' in host_name:
            host_names = host_name.split(':')
            host = host_names[0]
            try:
                port = int(host_names[1])
            except:
                print('Invalid port specified for host connection:', host_name[1])
                return False
        else:
            host = host_name
            port = 80

        argList = ''
        for arg, (val, dt) in action_arguments.items():
            argList += '<%s>%s</%s>' % (arg, val, arg)

        body = '<?xml version="1.0"?>\n' \
                   '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" '\
                   'SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">\n' \
                   '<SOAP-ENV:Body>\n' \
                   '<m:%s xmlns:m="%s">\n' \
                   '%s\n' \
                   '</m:%s>\n' \
                   '</SOAP-ENV:Body>\n' \
                   '</SOAP-ENV:Envelope>\n' % (action_name, service_type, argList, action_name)

        headers = {
            'Host': host_name,
            'Content-Length': len(body.encode('ascii')),
            'Content-Type': 'text/xml',
            'SOAPAction': '"%s#%s"' % (service_type, action_name)
        }

        for head, value in headers.items():
            request += '%s: %s\r\n' % (head, value)
        request += '\r\n%s' % body
        soap_envelope_end = re.compile('<\/.*:envelope>')

        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.connect((host, port))

            sock.send(request.encode('ascii'))
            response = ''
            while True:
                data = sock.recv(8192)
                if not data:
                    break
                else:
                    response += data.decode('UTF-8')

                    if soap_envelope_end.search(response.lower()) is not None:
                        break
            sock.close()

            (header, body) = response.split('\r\n\r\n', 1)
            if not header.upper().startswith('HTTP/1.') and ' 200 ' in header.split('\r\n')[0]:
                print('SOAP request failed with error code:', header.split('\r\n')[0].split(' ', 1)[1])
                #print(UpnpSoap.extractSingleTag(body, 'errorDescription'))
                return False
            else:
                return body
        except Exception as e:
            print('UpnpSoap.send: Caught socket exception:', e)
            sock.close()
            return False
        except KeyboardInterrupt:
            sock.close()
            return False

    # Send GET request for a UPNP XML file
    @staticmethod
    def get(url):
        headers = {
            'CONTENT-TYPE': 'text/xml; charset="utf-8"',
            'USER-AGENT': 'uPNP/1.0'
        }
        try:
            timeout = urllib3.util.timeout.Timeout(connect=2.0, read=7.0)
            http = urllib3.PoolManager(timeout=timeout)
            r = http.request("GET", url, headers=headers)
            return r.status, r.data
        except Exception as e:
            print("Request for '%s' failed: %s" % (url, e))
            return False, False
