# Exemplos qualitativos: top-5 de cada modelo


## q01 (identificador): `CVE-2021-44228`

| modelo | pos. | escore | site | título |
|---|---:|---:|---|---|
| jaccard | 1 | 0.0419 | exploit-db | Apache Log4j2 2.14.1 - Information Disclosure |
|  | 2 | 0.0395 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 3 | 0.0369 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 4 | 0.0035 | cwe | CWE-917: Improper Neutralization of Special Elements used in an Expression Language Statem |
|  | 5 | 0.0020 | cwe | CWE-1395: Dependency on Vulnerable Third-Party Component |
| tfidf | 1 | 772.1589 | exploit-db | Apache Log4j2 2.14.1 - Information Disclosure |
|  | 2 | 772.1589 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 3 | 565.2343 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 4 | 179.1548 | cwe | CWE-1395: Dependency on Vulnerable Third-Party Component |
|  | 5 | 179.1548 | cwe | CWE-917: Improper Neutralization of Special Elements used in an Expression Language Statem |
| vetorial | 1 | 0.2351 | exploit-db | Apache Log4j2 2.14.1 - Information Disclosure |
|  | 2 | 0.1822 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 3 | 0.1753 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 4 | 0.0536 | cwe | CWE-917: Improper Neutralization of Special Elements used in an Expression Language Statem |
|  | 5 | 0.0300 | cwe | CWE-1395: Dependency on Vulnerable Third-Party Component |
| bm1 | 1 | 27.4317 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 2 | 27.4317 | exploit-db | Apache Log4j2 2.14.1 - Information Disclosure |
|  | 3 | 27.4317 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 4 | 13.2693 | cwe | CWE-1395: Dependency on Vulnerable Third-Party Component |
|  | 5 | 13.2693 | cwe | CWE-917: Improper Neutralization of Special Elements used in an Expression Language Statem |
| bm15 | 1 | 37.7186 | exploit-db | Apache Log4j2 2.14.1 - Information Disclosure |
|  | 2 | 37.7186 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 3 | 32.4077 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 4 | 13.2693 | cwe | CWE-1395: Dependency on Vulnerable Third-Party Component |
|  | 5 | 13.2693 | cwe | CWE-917: Improper Neutralization of Special Elements used in an Expression Language Statem |
| bm11 | 1 | 46.5431 | exploit-db | Apache Log4j2 2.14.1 - Information Disclosure |
|  | 2 | 44.0577 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 3 | 40.6634 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 4 | 4.6233 | cwe | CWE-917: Improper Neutralization of Special Elements used in an Expression Language Statem |
|  | 5 | 2.6175 | cwe | CWE-1395: Dependency on Vulnerable Third-Party Component |
| bm25 | 1 | 43.8703 | exploit-db | Apache Log4j2 2.14.1 - Information Disclosure |
|  | 2 | 42.0931 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 3 | 38.1947 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 4 | 5.5230 | cwe | CWE-917: Improper Neutralization of Special Elements used in an Expression Language Statem |
|  | 5 | 3.2747 | cwe | CWE-1395: Dependency on Vulnerable Third-Party Component |
| bm25f | 1 | 24.9136 | exploit-db | Apache Log4j2 2.14.1 - Information Disclosure |
|  | 2 | 24.5731 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 3 | 23.9261 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 4 | 5.3638 | cwe | CWE-917: Improper Neutralization of Special Elements used in an Expression Language Statem |
|  | 5 | 3.1264 | cwe | CWE-1395: Dependency on Vulnerable Third-Party Component |

## q05 (produto+falha): `sql injection wordpress plugin`

| modelo | pos. | escore | site | título |
|---|---:|---:|---|---|
| jaccard | 1 | 0.2522 | exploit-db | WordPress Plugin Wordspew - SQL Injection |
|  | 2 | 0.2414 | exploit-db | WordPress Plugin st_newsletter - SQL Injection |
|  | 3 | 0.2243 | exploit-db | WordPress Plugin Download - 'dl_id' SQL Injection |
|  | 4 | 0.2242 | exploit-db | WordPress Plugin WP-Forum 1.7.8 - SQL Injection |
|  | 5 | 0.2196 | exploit-db | WordPress Plugin wptouch - SQL Injection |
| tfidf | 1 | 470.9636 | exploit-db | Multiple WordPress Plugins - 'timthumb.php' File Upload |
|  | 2 | 463.7374 | exploit-db | WordPress Plugin Spider Catalog 1.4.6 - Multiple Vulnerabilities |
|  | 3 | 448.5836 | exploit-db | WordPress Core / MU / Plugins - '/admin.php' Privileges Unchecked / Multiple Information D |
|  | 4 | 421.8700 | exploit-db | LearnPress WordPress LMS Plugin 4.2.7 - SQL Injection |
|  | 5 | 421.2333 | exploit-db | WordPress Plugin Spider Event Calendar 1.3.0 - Multiple Vulnerabilities |
| vetorial | 1 | 0.3914 | exploit-db | WordPress Plugin Tagged Albums - 'id' SQL Injection |
|  | 2 | 0.3732 | exploit-db | WordPress Plugin PHP Event Calendar - 'cid' SQL Injection |
|  | 3 | 0.3392 | exploit-db | WordPress Plugin Automatic 2.0.3 - SQL Injection |
|  | 4 | 0.3382 | exploit-db | WordPress Plugin Easy Career Openings - 'jobid' SQL Injection |
|  | 5 | 0.3355 | exploit-db | WordPress Plugin WP Feed - 'nid' SQL Injection |
| bm1 | 1 | 29.3951 | exploit-db | WordPress Plugin Photo Album Plus 4.1.1 - SQL Injection |
|  | 2 | 29.3951 | exploit-db | WordPress Plugin Contact Form 2.7.5 - SQL Injection |
|  | 3 | 29.3951 | exploit-db | WordPress Plugin GD Star Rating 1.9.10 - SQL Injection |
|  | 4 | 29.3951 | exploit-db | WordPress Plugin NextGEN Smooth Gallery 0.12 - Blind SQL Injection |
|  | 5 | 29.3951 | exploit-db | WordPress Plugin WP-SpamFree Spam Plugin - SQL Injection |
| bm15 | 1 | 49.9174 | exploit-db | WordPress Plugin All In One WP Security 3.8.2 - SQL Injection |
|  | 2 | 49.5983 | exploit-db | LearnPress WordPress LMS Plugin 4.2.7 - SQL Injection |
|  | 3 | 48.8522 | exploit-db | WordPress Plugin Simple Ads Manager - Multiple SQL Injections |
|  | 4 | 48.8347 | exploit-db | WordPress Plugin Booking Calendar 8.4.3 - (Authenticated) SQL Injection |
|  | 5 | 48.8233 | exploit-db | WordPress Plugin Count Per Day 3.4 - SQL Injection |
| bm11 | 1 | 58.0440 | exploit-db | WordPress Plugin Ocim MP3 - SQL Injection |
|  | 2 | 57.2825 | exploit-db | WordPress Plugin Glossary - SQL Injection |
|  | 3 | 57.1018 | exploit-db | WordPress Plugin ProPlayer 4.7.9.1 - SQL Injection |
|  | 4 | 57.0961 | exploit-db | WordPress Plugin Symposium 0.64 - SQL Injection |
|  | 5 | 57.0400 | exploit-db | WordPress Plugin Donation 1.0 - SQL Injection |
| bm25 | 1 | 53.8058 | exploit-db | WordPress Plugin Ocim MP3 - SQL Injection |
|  | 2 | 53.7280 | exploit-db | WordPress Plugin Booking Calendar 8.4.3 - (Authenticated) SQL Injection |
|  | 3 | 53.3789 | exploit-db | WordPress Plugin Calculated Fields Form 1.0.10 - SQL Injection |
|  | 4 | 53.3038 | exploit-db | WordPress Plugin Business Intelligence - SQL Injection (Metasploit) |
|  | 5 | 53.2057 | exploit-db | WordPress Plugin Glossary - SQL Injection |
| bm25f | 1 | 26.1764 | exploit-db | WordPress Plugin Booking Calendar 8.4.3 - (Authenticated) SQL Injection |
|  | 2 | 26.1622 | exploit-db | WordPress Plugin Ocim MP3 - SQL Injection |
|  | 3 | 26.1023 | exploit-db | WordPress Plugin Business Intelligence - SQL Injection (Metasploit) |
|  | 4 | 26.0880 | exploit-db | WordPress Plugin Donation 1.0 - SQL Injection |
|  | 5 | 26.0553 | exploit-db | WordPress Plugin Glossary - SQL Injection |

## q12 (conceito): `log4j`

| modelo | pos. | escore | site | título |
|---|---:|---:|---|---|
| jaccard | 1 | 0.0395 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 2 | 0.0062 | exploit-db | Apache Log4j2 2.14.1 - Information Disclosure |
|  | 3 | 0.0057 | github | Apache Log4j JSON Template Layout: Improper serialization of non-finite floating-point val |
|  | 4 | 0.0056 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 5 | 0.0056 | github | Apache Log4j Core: `verifyHostName` attribute silently ignored in TLS configuration |
| tfidf | 1 | 886.5451 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 2 | 790.0130 | github | Apache Log4j 1 to Log4j 2 bridge: silent log event loss in Log4j1XmlLayout due to unescape |
|  | 3 | 699.6281 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 4 | 627.7325 | github | Apache Log4j API: Improper encoding of non-finite floating-point values during MapMessage  |
|  | 5 | 573.1519 | github | Apache Log4j Core: `verifyHostName` attribute silently ignored in TLS configuration |
| vetorial | 1 | 0.2831 | github | Apache Log4j 1 to Log4j 2 bridge: silent log event loss in Log4j1XmlLayout due to unescape |
|  | 2 | 0.2384 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 3 | 0.2128 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 4 | 0.2103 | github | Apache Log4j Core: `verifyHostName` attribute silently ignored in TLS configuration |
|  | 5 | 0.2053 | github | Apache Log4j JSON Template Layout: Improper serialization of non-finite floating-point val |
| bm1 | 1 | 26.0145 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 2 | 13.7998 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 3 | 13.7998 | exploit-db | ABB Cylon Aspect Studio 3.08.03 - Binary Planting |
|  | 4 | 13.7998 | exploit-db | Apache Log4j2 2.14.1 - Information Disclosure |
|  | 5 | 12.2147 | cwe | CWE-1395: Dependency on Vulnerable Third-Party Component |
| bm15 | 1 | 40.1487 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 2 | 25.2997 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 3 | 25.2759 | github | Apache Log4j 1 to Log4j 2 bridge: silent log event loss in Log4j1XmlLayout due to unescape |
|  | 4 | 23.7108 | github | Apache Log4j API: Improper encoding of non-finite floating-point values during MapMessage  |
|  | 5 | 22.9397 | github | Apache Log4j Core: `verifyHostName` attribute silently ignored in TLS configuration |
| bm11 | 1 | 45.9838 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 2 | 26.4239 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 3 | 22.8375 | github | Apache Log4j 1 to Log4j 2 bridge: silent log event loss in Log4j1XmlLayout due to unescape |
|  | 4 | 21.0231 | exploit-db | Apache Log4j2 2.14.1 - Information Disclosure |
|  | 5 | 18.9278 | github | Apache Log4j API: Improper encoding of non-finite floating-point values during MapMessage  |
| bm25 | 1 | 44.1754 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 2 | 26.1336 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 3 | 23.4019 | github | Apache Log4j 1 to Log4j 2 bridge: silent log event loss in Log4j1XmlLayout due to unescape |
|  | 4 | 20.4707 | exploit-db | Apache Log4j2 2.14.1 - Information Disclosure |
|  | 5 | 19.9330 | github | Apache Log4j API: Improper encoding of non-finite floating-point values during MapMessage  |
| bm25f | 1 | 23.2175 | github | Apache Log4j 1 to Log4j 2 bridge: silent log event loss in Log4j1XmlLayout due to unescape |
|  | 2 | 22.9260 | exploit-db | Apache Log4j 2 - Remote Code Execution (RCE) |
|  | 3 | 22.5833 | exploit-db | AD Manager Plus 7122 - Remote Code Execution (RCE) |
|  | 4 | 20.6888 | github | Apache Log4j Core: `verifyHostName` attribute silently ignored in TLS configuration |
|  | 5 | 20.5010 | github | Apache Log4j API: Improper encoding of non-finite floating-point values during MapMessage  |

## q18 (codigo): `strcpy stack overflow`

| modelo | pos. | escore | site | título |
|---|---:|---:|---|---|
| jaccard | 1 | 0.1422 | exploit-db | Adobe Acrobat 9.1.1 (OSX/Windows) - Stack Overflow Crash (PoC) |
|  | 2 | 0.1255 | exploit-db | mpegable Player 2.12 - '.yuv' Local Stack Overflow (PoC) |
|  | 3 | 0.1238 | exploit-db | Adobe Reader - 'util.printf()' JavaScript Function Stack Overflow (1) |
|  | 4 | 0.1181 | exploit-db | Sorinara Streaming Audio Player 0.9 - '.pla' Local Stack Overflow (PoC) |
|  | 5 | 0.1160 | exploit-db | MixVibes Pro 7.043 - '.vib' Local Stack Overflow (PoC) |
| tfidf | 1 | 671.2103 | cwe | CWE-676: Use of Potentially Dangerous Function |
|  | 2 | 613.8223 | cwe | CWE-120: Buffer Copy without Checking Size of Input ('Classic Buffer Overflow') |
|  | 3 | 428.4940 | cwe | CWE-754: Improper Check for Unusual or Exceptional Conditions |
|  | 4 | 408.7113 | cwe | CWE-787: Out-of-bounds Write |
|  | 5 | 400.4502 | cwe | CWE-252: Unchecked Return Value |
| vetorial | 1 | 0.2175 | rapid7 | CVE-2026-98097: Linux: In the Linux kernel, the following vulnerability has been resolved: |
|  | 2 | 0.1784 | rapid7 | CVE-2026-90680: Stack-based Buffer Overflow |
|  | 3 | 0.1768 | exploit-db | xsplumber - 'strcpy()' Local Buffer Overflow |
|  | 4 | 0.1595 | rapid7 | CVE-2025-64031: Heap-based Buffer Overflow |
|  | 5 | 0.1584 | cwe | CWE-676: Use of Potentially Dangerous Function |
| bm1 | 1 | 27.0597 | cwe | CWE-754: Improper Check for Unusual or Exceptional Conditions |
|  | 2 | 27.0597 | cwe | CWE-119: Improper Restriction of Operations within the Bounds of a Memory Buffer |
|  | 3 | 27.0597 | cwe | CWE-787: Out-of-bounds Write |
|  | 4 | 27.0597 | cwe | CWE-120: Buffer Copy without Checking Size of Input ('Classic Buffer Overflow') |
|  | 5 | 25.3034 | exploit-db | xsplumber - 'strcpy()' Local Buffer Overflow |
| bm15 | 1 | 43.7308 | cwe | CWE-120: Buffer Copy without Checking Size of Input ('Classic Buffer Overflow') |
|  | 2 | 37.9964 | cwe | CWE-787: Out-of-bounds Write |
|  | 3 | 36.4296 | exploit-db | CA BrightStor ARCserve - 'msgeng.exe' Remote Stack Overflow |
|  | 4 | 35.8818 | cwe | CWE-754: Improper Check for Unusual or Exceptional Conditions |
|  | 5 | 35.7595 | cwe | CWE-676: Use of Potentially Dangerous Function |
| bm11 | 1 | 43.1391 | exploit-db | xsplumber - 'strcpy()' Local Buffer Overflow |
|  | 2 | 38.2877 | exploit-db | Xilisoft Video Converter Wizard 3 - '.cue' Stack Buffer Overflow (PoC) |
|  | 3 | 37.7196 | exploit-db | ABC2MTEX 1.6.1 - Command Line Stack Overflow |
|  | 4 | 36.5156 | exploit-db | Dameware Mini Remote Control 4.0 - Username Stack Buffer Overflow (Metasploit) |
|  | 5 | 34.5383 | exploit-db | mcrypt 2.5.8 - Local Stack Overflow |
| bm25 | 1 | 40.0026 | exploit-db | xsplumber - 'strcpy()' Local Buffer Overflow |
|  | 2 | 35.5242 | exploit-db | Xilisoft Video Converter Wizard 3 - '.cue' Stack Buffer Overflow (PoC) |
|  | 3 | 35.4572 | exploit-db | ABC2MTEX 1.6.1 - Command Line Stack Overflow |
|  | 4 | 34.5864 | exploit-db | Dameware Mini Remote Control 4.0 - Username Stack Buffer Overflow (Metasploit) |
|  | 5 | 33.8669 | exploit-db | IPSwitch IMail Server 2006 - SEARCH Remote Stack Overflow |
| bm25f | 1 | 24.7817 | cwe | CWE-121: Stack-based Buffer Overflow |
|  | 2 | 23.5532 | exploit-db | Apple Mac OSX EvoCam Web Server (Snow Leopard) - ROP Remote Overflow |
|  | 3 | 23.4622 | exploit-db | ABC2MTEX 1.6.1 - Command Line Stack Overflow |
|  | 4 | 22.9375 | exploit-db | Oops Proxy Server 1.4.22 - Remote Buffer Overflow (1) |
|  | 5 | 22.8147 | exploit-db | DATAC RealWin SCADA Server 2.0 (Build 6.1.8.10) - Buffer Overflow |
