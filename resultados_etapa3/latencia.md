Latência por consulta e modelo (5 repetições após 1 de aquecimento, k = 10).

| id | consulta | modelo | candidatos | escore > 0 | postings lidos | ms média | ms mediana | ms máx. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| q01 | CVE-2021-44228 | jaccard | 6 | 6 | 9 | 0.06 | 0.06 | 0.08 |
| q01 | CVE-2021-44228 | tfidf | 6 | 6 | 9 | 0.06 | 0.06 | 0.06 |
| q01 | CVE-2021-44228 | vetorial | 6 | 6 | 9 | 0.06 | 0.06 | 0.07 |
| q01 | CVE-2021-44228 | bm1 | 6 | 6 | 9 | 0.06 | 0.05 | 0.07 |
| q01 | CVE-2021-44228 | bm15 | 6 | 6 | 9 | 0.05 | 0.05 | 0.06 |
| q01 | CVE-2021-44228 | bm11 | 6 | 6 | 9 | 0.05 | 0.05 | 0.05 |
| q01 | CVE-2021-44228 | bm25 | 6 | 6 | 9 | 0.05 | 0.05 | 0.06 |
| q01 | CVE-2021-44228 | bm25f | 6 | 6 | 9 | 0.06 | 0.06 | 0.07 |
| q02 | MS17-010 | jaccard | 5 | 5 | 9 | 0.07 | 0.06 | 0.07 |
| q02 | MS17-010 | tfidf | 5 | 5 | 9 | 0.07 | 0.07 | 0.07 |
| q02 | MS17-010 | vetorial | 5 | 5 | 9 | 0.07 | 0.07 | 0.07 |
| q02 | MS17-010 | bm1 | 5 | 5 | 9 | 0.06 | 0.06 | 0.06 |
| q02 | MS17-010 | bm15 | 5 | 5 | 9 | 0.06 | 0.06 | 0.07 |
| q02 | MS17-010 | bm11 | 5 | 5 | 9 | 0.06 | 0.06 | 0.07 |
| q02 | MS17-010 | bm25 | 5 | 5 | 9 | 0.07 | 0.07 | 0.07 |
| q02 | MS17-010 | bm25f | 5 | 5 | 9 | 0.07 | 0.07 | 0.07 |
| q03 | CWE-79 | jaccard | 809 | 809 | 810 | 1.27 | 1.26 | 1.28 |
| q03 | CWE-79 | tfidf | 809 | 809 | 810 | 1.36 | 1.35 | 1.39 |
| q03 | CWE-79 | vetorial | 809 | 809 | 810 | 1.50 | 1.50 | 1.52 |
| q03 | CWE-79 | bm1 | 809 | 809 | 810 | 1.14 | 1.15 | 1.15 |
| q03 | CWE-79 | bm15 | 809 | 809 | 810 | 1.22 | 1.22 | 1.23 |
| q03 | CWE-79 | bm11 | 809 | 809 | 810 | 1.31 | 1.24 | 1.56 |
| q03 | CWE-79 | bm25 | 809 | 809 | 810 | 1.33 | 1.33 | 1.41 |
| q03 | CWE-79 | bm25f | 809 | 809 | 810 | 2.05 | 2.03 | 2.19 |
| q04 | SA-CORE-2018-002 | jaccard | 7 | 7 | 7 | 0.05 | 0.05 | 0.06 |
| q04 | SA-CORE-2018-002 | tfidf | 7 | 7 | 7 | 0.05 | 0.05 | 0.05 |
| q04 | SA-CORE-2018-002 | vetorial | 7 | 7 | 7 | 0.06 | 0.06 | 0.06 |
| q04 | SA-CORE-2018-002 | bm1 | 7 | 7 | 7 | 0.05 | 0.05 | 0.05 |
| q04 | SA-CORE-2018-002 | bm15 | 7 | 7 | 7 | 0.05 | 0.05 | 0.06 |
| q04 | SA-CORE-2018-002 | bm11 | 7 | 7 | 7 | 0.05 | 0.05 | 0.05 |
| q04 | SA-CORE-2018-002 | bm25 | 7 | 7 | 7 | 0.06 | 0.05 | 0.09 |
| q04 | SA-CORE-2018-002 | bm25f | 7 | 7 | 7 | 0.06 | 0.06 | 0.07 |
| q05 | sql injection wordpress plugin | jaccard | 18291 | 18291 | 49738 | 60.88 | 58.45 | 72.61 |
| q05 | sql injection wordpress plugin | tfidf | 18291 | 18291 | 49738 | 80.26 | 75.20 | 89.21 |
| q05 | sql injection wordpress plugin | vetorial | 18291 | 18291 | 49738 | 82.04 | 85.37 | 88.31 |
| q05 | sql injection wordpress plugin | bm1 | 18291 | 18291 | 49738 | 69.69 | 73.48 | 74.87 |
| q05 | sql injection wordpress plugin | bm15 | 18291 | 18291 | 49738 | 75.02 | 78.59 | 80.41 |
| q05 | sql injection wordpress plugin | bm11 | 18291 | 18291 | 49738 | 77.25 | 80.16 | 82.38 |
| q05 | sql injection wordpress plugin | bm25 | 18291 | 18291 | 49738 | 80.84 | 84.56 | 88.36 |
| q05 | sql injection wordpress plugin | bm25f | 18291 | 18291 | 49738 | 115.81 | 120.22 | 124.13 |
| q06 | remote code execution apache struts | jaccard | 42772 | 42772 | 80430 | 113.98 | 108.84 | 127.64 |
| q06 | remote code execution apache struts | tfidf | 42772 | 42772 | 80430 | 135.59 | 130.33 | 148.63 |
| q06 | remote code execution apache struts | vetorial | 42772 | 42772 | 80430 | 138.90 | 144.99 | 145.96 |
| q06 | remote code execution apache struts | bm1 | 42772 | 42772 | 80430 | 116.56 | 121.20 | 123.42 |
| q06 | remote code execution apache struts | bm15 | 42772 | 42772 | 80430 | 128.58 | 131.29 | 132.36 |
| q06 | remote code execution apache struts | bm11 | 42772 | 42772 | 80430 | 127.32 | 130.77 | 136.28 |
| q06 | remote code execution apache struts | bm25 | 42772 | 42772 | 80430 | 136.86 | 142.18 | 152.19 |
| q06 | remote code execution apache struts | bm25f | 42772 | 42772 | 80430 | 204.55 | 202.82 | 219.13 |
| q07 | cross site scripting drupal | jaccard | 20032 | 20032 | 54834 | 66.18 | 61.08 | 77.94 |
| q07 | cross site scripting drupal | tfidf | 20032 | 20032 | 54834 | 90.31 | 94.49 | 96.24 |
| q07 | cross site scripting drupal | vetorial | 20032 | 20032 | 54834 | 85.43 | 81.18 | 94.55 |
| q07 | cross site scripting drupal | bm1 | 20032 | 20032 | 54834 | 78.44 | 80.88 | 83.43 |
| q07 | cross site scripting drupal | bm15 | 20032 | 20032 | 54834 | 78.50 | 73.69 | 88.12 |
| q07 | cross site scripting drupal | bm11 | 20032 | 20032 | 54834 | 81.96 | 85.51 | 87.87 |
| q07 | cross site scripting drupal | bm25 | 20032 | 20032 | 54834 | 82.24 | 77.08 | 93.13 |
| q07 | cross site scripting drupal | bm25f | 20032 | 20032 | 54834 | 126.58 | 130.18 | 133.24 |
| q08 | joomla sql injection | jaccard | 16318 | 16318 | 44374 | 58.79 | 54.09 | 68.16 |
| q08 | joomla sql injection | tfidf | 16318 | 16318 | 44374 | 72.80 | 67.76 | 81.37 |
| q08 | joomla sql injection | vetorial | 16318 | 16318 | 44374 | 79.73 | 79.58 | 90.60 |
| q08 | joomla sql injection | bm1 | 16318 | 16318 | 44374 | 62.68 | 56.63 | 74.13 |
| q08 | joomla sql injection | bm15 | 16318 | 16318 | 44374 | 66.07 | 62.66 | 74.76 |
| q08 | joomla sql injection | bm11 | 16318 | 16318 | 44374 | 66.87 | 63.78 | 75.18 |
| q08 | joomla sql injection | bm25 | 16318 | 16318 | 44374 | 71.22 | 74.57 | 78.03 |
| q08 | joomla sql injection | bm25f | 16318 | 16318 | 44374 | 100.91 | 95.85 | 112.50 |
| q09 | buffer overflow windows smb | jaccard | 19156 | 19156 | 44556 | 62.63 | 59.27 | 70.12 |
| q09 | buffer overflow windows smb | tfidf | 19156 | 19156 | 44556 | 77.81 | 81.67 | 84.08 |
| q09 | buffer overflow windows smb | vetorial | 19156 | 19156 | 44556 | 75.01 | 69.44 | 86.29 |
| q09 | buffer overflow windows smb | bm1 | 19156 | 19156 | 44556 | 68.79 | 62.86 | 82.85 |
| q09 | buffer overflow windows smb | bm15 | 19156 | 19156 | 44556 | 69.72 | 65.82 | 79.61 |
| q09 | buffer overflow windows smb | bm11 | 19156 | 19156 | 44556 | 73.88 | 74.95 | 83.47 |
| q09 | buffer overflow windows smb | bm25 | 19156 | 19156 | 44556 | 83.78 | 81.14 | 106.21 |
| q09 | buffer overflow windows smb | bm25f | 19156 | 19156 | 44556 | 105.30 | 103.16 | 113.70 |
| q10 | openssh vulnerability | jaccard | 59469 | 59469 | 80218 | 128.23 | 133.67 | 136.74 |
| q10 | openssh vulnerability | tfidf | 59469 | 59469 | 80218 | 137.56 | 142.74 | 149.62 |
| q10 | openssh vulnerability | vetorial | 59469 | 59469 | 80218 | 152.29 | 153.87 | 159.89 |
| q10 | openssh vulnerability | bm1 | 59469 | 20709 | 80218 | 109.63 | 114.18 | 117.24 |
| q10 | openssh vulnerability | bm15 | 59469 | 20709 | 80218 | 116.51 | 119.84 | 123.74 |
| q10 | openssh vulnerability | bm11 | 59469 | 20709 | 80218 | 121.71 | 126.48 | 132.66 |
| q10 | openssh vulnerability | bm25 | 59469 | 20709 | 80218 | 124.82 | 126.93 | 129.15 |
| q10 | openssh vulnerability | bm25f | 59469 | 62 | 80218 | 180.61 | 180.75 | 199.76 |
| q11 | privilege escalation linux kernel | jaccard | 22812 | 22812 | 33137 | 47.64 | 45.57 | 58.40 |
| q11 | privilege escalation linux kernel | tfidf | 22812 | 22812 | 33137 | 59.86 | 58.07 | 68.12 |
| q11 | privilege escalation linux kernel | vetorial | 22812 | 22812 | 33137 | 60.46 | 56.03 | 69.41 |
| q11 | privilege escalation linux kernel | bm1 | 22812 | 22812 | 33137 | 49.43 | 44.72 | 57.60 |
| q11 | privilege escalation linux kernel | bm15 | 22812 | 22812 | 33137 | 55.41 | 50.84 | 64.94 |
| q11 | privilege escalation linux kernel | bm11 | 22812 | 22812 | 33137 | 55.38 | 52.08 | 62.34 |
| q11 | privilege escalation linux kernel | bm25 | 22812 | 22812 | 33137 | 55.88 | 49.86 | 66.81 |
| q11 | privilege escalation linux kernel | bm25f | 22812 | 22812 | 33137 | 92.83 | 87.17 | 104.73 |
| q12 | log4j | jaccard | 16 | 16 | 17 | 0.08 | 0.08 | 0.09 |
| q12 | log4j | tfidf | 16 | 16 | 17 | 0.09 | 0.09 | 0.11 |
| q12 | log4j | vetorial | 16 | 16 | 17 | 0.09 | 0.09 | 0.09 |
| q12 | log4j | bm1 | 16 | 16 | 17 | 0.08 | 0.08 | 0.08 |
| q12 | log4j | bm15 | 16 | 16 | 17 | 0.09 | 0.08 | 0.11 |
| q12 | log4j | bm11 | 16 | 16 | 17 | 0.08 | 0.08 | 0.08 |
| q12 | log4j | bm25 | 16 | 16 | 17 | 0.09 | 0.09 | 0.12 |
| q12 | log4j | bm25f | 16 | 16 | 17 | 0.10 | 0.10 | 0.11 |
| q13 | path traversal | jaccard | 16657 | 16657 | 20992 | 38.73 | 35.35 | 52.68 |
| q13 | path traversal | tfidf | 16657 | 16657 | 20992 | 43.58 | 39.93 | 51.71 |
| q13 | path traversal | vetorial | 16657 | 16657 | 20992 | 45.74 | 40.96 | 54.07 |
| q13 | path traversal | bm1 | 16657 | 16657 | 20992 | 35.16 | 33.10 | 44.76 |
| q13 | path traversal | bm15 | 16657 | 16657 | 20992 | 37.13 | 34.76 | 47.36 |
| q13 | path traversal | bm11 | 16657 | 16657 | 20992 | 40.17 | 35.17 | 48.13 |
| q13 | path traversal | bm25 | 16657 | 16657 | 20992 | 38.62 | 37.14 | 48.50 |
| q13 | path traversal | bm25f | 16657 | 16657 | 20992 | 58.60 | 54.33 | 68.32 |
| q14 | java deserialization | jaccard | 2271 | 2271 | 2790 | 4.94 | 4.93 | 5.01 |
| q14 | java deserialization | tfidf | 2271 | 2271 | 2790 | 5.38 | 5.33 | 5.62 |
| q14 | java deserialization | vetorial | 2271 | 2271 | 2790 | 5.92 | 5.77 | 6.61 |
| q14 | java deserialization | bm1 | 2271 | 2271 | 2790 | 4.64 | 4.63 | 4.74 |
| q14 | java deserialization | bm15 | 2271 | 2271 | 2790 | 4.91 | 4.90 | 4.99 |
| q14 | java deserialization | bm11 | 2271 | 2271 | 2790 | 7.73 | 5.17 | 17.07 |
| q14 | java deserialization | bm25 | 2271 | 2271 | 2790 | 5.09 | 5.10 | 5.11 |
| q14 | java deserialization | bm25f | 2271 | 2271 | 2790 | 8.22 | 7.77 | 10.02 |
| q15 | denial of service | jaccard | 11132 | 11132 | 21990 | 33.12 | 30.03 | 41.02 |
| q15 | denial of service | tfidf | 11132 | 11132 | 21990 | 36.59 | 34.34 | 46.87 |
| q15 | denial of service | vetorial | 11132 | 11132 | 21990 | 39.59 | 34.97 | 48.36 |
| q15 | denial of service | bm1 | 11132 | 11132 | 21990 | 30.81 | 27.92 | 41.40 |
| q15 | denial of service | bm15 | 11132 | 11132 | 21990 | 33.18 | 30.61 | 43.41 |
| q15 | denial of service | bm11 | 11132 | 11132 | 21990 | 34.38 | 32.22 | 45.41 |
| q15 | denial of service | bm25 | 11132 | 11132 | 21990 | 34.12 | 32.49 | 41.99 |
| q15 | denial of service | bm25f | 11132 | 11132 | 21990 | 52.95 | 50.24 | 64.74 |
| q16 | csrf token bypass | jaccard | 11959 | 11959 | 16275 | 27.67 | 24.89 | 38.24 |
| q16 | csrf token bypass | tfidf | 11959 | 11959 | 16275 | 31.41 | 28.94 | 41.92 |
| q16 | csrf token bypass | vetorial | 11959 | 11959 | 16275 | 33.18 | 30.48 | 43.05 |
| q16 | csrf token bypass | bm1 | 11959 | 11959 | 16275 | 26.69 | 24.27 | 37.36 |
| q16 | csrf token bypass | bm15 | 11959 | 11959 | 16275 | 29.15 | 27.38 | 38.63 |
| q16 | csrf token bypass | bm11 | 11959 | 11959 | 16275 | 28.30 | 26.27 | 37.96 |
| q16 | csrf token bypass | bm25 | 11959 | 11959 | 16275 | 30.02 | 26.57 | 41.26 |
| q16 | csrf token bypass | bm25f | 11959 | 11959 | 16275 | 45.92 | 41.04 | 55.03 |
| q17 | use after free | jaccard | 25756 | 25756 | 34099 | 56.73 | 51.55 | 65.91 |
| q17 | use after free | tfidf | 25756 | 25756 | 34099 | 63.63 | 59.08 | 71.28 |
| q17 | use after free | vetorial | 25756 | 25756 | 34099 | 64.87 | 62.24 | 76.17 |
| q17 | use after free | bm1 | 25756 | 25756 | 34099 | 53.10 | 50.17 | 65.78 |
| q17 | use after free | bm15 | 25756 | 25756 | 34099 | 55.84 | 52.39 | 68.32 |
| q17 | use after free | bm11 | 25756 | 25756 | 34099 | 58.33 | 52.72 | 67.38 |
| q17 | use after free | bm25 | 25756 | 25756 | 34099 | 61.92 | 59.62 | 70.32 |
| q17 | use after free | bm25f | 25756 | 25756 | 34099 | 90.52 | 85.78 | 99.69 |
| q18 | strcpy stack overflow | jaccard | 8378 | 8378 | 16477 | 24.91 | 22.58 | 35.09 |
| q18 | strcpy stack overflow | tfidf | 8378 | 8378 | 16477 | 28.98 | 26.74 | 38.31 |
| q18 | strcpy stack overflow | vetorial | 8378 | 8378 | 16477 | 29.43 | 26.67 | 38.82 |
| q18 | strcpy stack overflow | bm1 | 8378 | 8378 | 16477 | 25.01 | 23.16 | 33.46 |
| q18 | strcpy stack overflow | bm15 | 8378 | 8378 | 16477 | 26.18 | 23.68 | 37.06 |
| q18 | strcpy stack overflow | bm11 | 8378 | 8378 | 16477 | 26.02 | 23.97 | 35.16 |
| q18 | strcpy stack overflow | bm25 | 8378 | 8378 | 16477 | 27.31 | 24.74 | 36.88 |
| q18 | strcpy stack overflow | bm25f | 8378 | 8378 | 16477 | 40.18 | 38.40 | 49.51 |
| q19 | codigo:shellcode | jaccard | 2983 | 2983 | 2983 | 8.87 | 6.48 | 18.47 |
| q19 | codigo:shellcode | tfidf | 2983 | 2983 | 2983 | 6.54 | 6.48 | 6.77 |
| q19 | codigo:shellcode | vetorial | 2983 | 2983 | 2983 | 7.09 | 7.03 | 7.33 |
| q19 | codigo:shellcode | bm1 | 2983 | 2983 | 2983 | 5.88 | 5.75 | 6.20 |
| q19 | codigo:shellcode | bm15 | 2983 | 2983 | 2983 | 6.19 | 6.01 | 6.54 |
| q19 | codigo:shellcode | bm11 | 2983 | 2983 | 2983 | 6.06 | 6.05 | 6.18 |
| q19 | codigo:shellcode | bm25 | 2983 | 2983 | 2983 | 9.12 | 6.40 | 19.52 |
| q19 | codigo:shellcode | bm25f | 2983 | 2983 | 2983 | 8.24 | 8.21 | 8.29 |
| q20 | codigo:system | jaccard | 10048 | 10048 | 10048 | 18.66 | 16.45 | 28.06 |
| q20 | codigo:system | tfidf | 10048 | 10048 | 10048 | 17.40 | 17.30 | 17.82 |
| q20 | codigo:system | vetorial | 10048 | 10048 | 10048 | 19.02 | 18.99 | 19.10 |
| q20 | codigo:system | bm1 | 10048 | 10048 | 10048 | 17.50 | 15.39 | 27.07 |
| q20 | codigo:system | bm15 | 10048 | 10048 | 10048 | 18.42 | 15.83 | 28.12 |
| q20 | codigo:system | bm11 | 10048 | 10048 | 10048 | 18.44 | 15.91 | 28.66 |
| q20 | codigo:system | bm25 | 10048 | 10048 | 10048 | 16.46 | 16.14 | 17.74 |
| q20 | codigo:system | bm25f | 10048 | 10048 | 10048 | 25.75 | 23.11 | 35.27 |
