# Exemplos de --explicar

## IDF baixo de um termo comum × IDF alto de um termo raro

### TF-IDF: 'exploit' (df alto) e 'strcpy' (df baixo)

`python ranquear.py "exploit strcpy" --modelo tfidf -k 3 --explicar`

```
1. 626.5046  cwe  CWE-676: Use of Potentially Dangerous Function
     · termo exploit  tf 1  TF 1  idf 0.3524  w_q 0.3524  w_d 0.3524  parcela 0.1242
     · termo strcpi  tf 9  TF 4.17  idf 11.8  w_q 11.8  w_d 49.2  parcela 580.6
     · termo c:strcpy  tf 1  TF 1  idf 6.765  w_q 6.765  w_d 6.765  parcela 45.77
2. 451.8748  cwe  CWE-120: Buffer Copy without Checking Size of Input ('Classic Buffer Overflow')
     · termo exploit  tf 5  TF 3.322  idf 0.3524  w_q 0.3524  w_d 1.171  parcela 0.4125
     · termo strcpi  tf 3  TF 2.585  idf 11.8  w_q 11.8  w_d 30.5  parcela 359.9
     · termo c:strcpy  tf 2  TF 2  idf 6.765  w_q 6.765  w_d 13.53  parcela 91.54
3. 370.1376  cwe  CWE-252: Unchecked Return Value
     · termo exploit  tf 1  TF 1  idf 0.3524  w_q 0.3524  w_d 0.3524  parcela 0.1242
     · termo strcpi  tf 2  TF 2  idf 11.8  w_q 11.8  w_d 23.6  parcela 278.5
     · termo c:strcpy  tf 2  TF 2  idf 6.765  w_q 6.765  w_d 13.53  parcela 91.54
```

### BM25: o IDF de 'exploit' (df > N/2) é limitado a 0

`python ranquear.py "exploit strcpy" --modelo bm25 -k 3 --explicar`

```
1. 28.7222  exploit-db  xsplumber - 'strcpy()' Local Buffer Overflow
     · termo exploit  campo texto  tf 1  len/avg 0.282  idf 0  peso 1  parcela 0
     · termo strcpi  campo texto  tf 2  len/avg 0.282  idf 11.76  peso 1  parcela 20.26
     · termo c:exploit  campo codigo  tf 1  len/avg 0.6035  idf 0.3378  peso 1  parcela 0.4032
     · termo c:strcpy  campo codigo  tf 1  len/avg 0.6035  idf 6.751  peso 1  parcela 8.058
2. 25.0187  cwe  CWE-676: Use of Potentially Dangerous Function
     · termo exploit  campo texto  tf 1  len/avg 8.453  idf 0  peso 1  parcela 0
     · termo strcpi  campo texto  tf 9  len/avg 8.453  idf 11.76  peso 1  parcela 13.77
     · termo c:strcpy  campo codigo  tf 1  len/avg 0.02277  idf 6.751  peso 1  parcela 11.25
3. 19.8956  cwe  CWE-1177: Use of Prohibited Code
     · termo strcpi  campo texto  tf 2  len/avg 3.925  idf 11.76  peso 1  parcela 8.871
     · termo c:strcpy  campo codigo  tf 1  len/avg 0.05238  idf 6.751  peso 1  parcela 11.02
```

## Efeito do título no BM25F

### BM25F com peso do título 1

`python ranquear.py "sql injection wordpress plugin" --modelo bm25f peso_titulo=1 -k 5 --explicar`

```
1. 25.9893  exploit-db  WordPress Plugin Booking Calendar 8.4.3 - (Authenticated) SQL Injection
     · palavra sql  campos {titulo {tf 1, len/avg 1.056, w·tf/B 0.9599}, corpo {tf 2, len/avg 0.3074, w·tf/B 4.162}, codigo {tf 7, len/avg 0.7493, w·tf/B 8.621}}  tf~ 13.74  n 10548  idf 2.346  parcela 4.747
     · palavra inject  campos {titulo {tf 1, len/avg 1.056, w·tf/B 0.9599}, corpo {tf 2, len/avg 0.3074, w·tf/B 4.162}, codigo {tf 8, len/avg 0.7493, w·tf/B 9.853}}  tf~ 14.97  n 14907  idf 1.725  parcela 3.513
     · palavra wordpress  campos {titulo {tf 1, len/avg 1.056, w·tf/B 0.9599}, corpo {tf 1, len/avg 0.3074, w·tf/B 2.081}, codigo {tf 8, len/avg 0.7493, w·tf/B 9.853}}  tf~ 12.89  n 2239  idf 4.79  parcela 9.64
     · palavra plugin  campos {titulo {tf 1, len/avg 1.056, w·tf/B 0.9599}, corpo {tf 1, len/avg 0.3074, w·tf/B 2.081}, codigo {tf 5, len/avg 0.7493, w·tf/B 6.158}}  tf~ 9.199  n 3407  idf 4.157  parcela 8.089
2. 25.9296  exploit-db  WordPress Plugin Ocim MP3 - SQL Injection
     · palavra sql  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 1.185}, corpo {tf 1, len/avg 0.2831, w·tf/B 2.163}, codigo {tf 3, len/avg 0.1868, w·tf/B 7.691}}  tf~ 11.04  n 10548  idf 2.346  parcela 4.655
     · palavra inject  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 1.185}, corpo {tf 1, len/avg 0.2831, w·tf/B 2.163}, codigo {tf 3, len/avg 0.1868, w·tf/B 7.691}}  tf~ 11.04  n 14907  idf 1.725  parcela 3.422
     · palavra wordpress  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 1.185}, corpo {tf 2, len/avg 0.2831, w·tf/B 4.326}, codigo {tf 2, len/avg 0.1868, w·tf/B 5.127}}  tf~ 10.64  n 2239  idf 4.79  parcela 9.469
     · palavra plugin  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 1.185}, corpo {tf 2, len/avg 0.2831, w·tf/B 4.326}, codigo {tf 3, len/avg 0.1868, w·tf/B 7.691}}  tf~ 13.2  n 3407  idf 4.157  parcela 8.383
3. 25.8857  exploit-db  WordPress Plugin Business Intelligence - SQL Injection (Metasploit)
     · palavra sql  campos {titulo {tf 1, len/avg 0.9237, w·tf/B 1.061}, corpo {tf 1, len/avg 0.3397, w·tf/B 1.981}, codigo {tf 6, len/avg 0.5215, w·tf/B 9.358}}  tf~ 12.4  n 10548  idf 2.346  parcela 4.706
     · palavra inject  campos {titulo {tf 1, len/avg 0.9237, w·tf/B 1.061}, corpo {tf 1, len/avg 0.3397, w·tf/B 1.981}, codigo {tf 4, len/avg 0.5215, w·tf/B 6.239}}  tf~ 9.28  n 14907  idf 1.725  parcela 3.36
     · palavra wordpress  campos {titulo {tf 1, len/avg 0.9237, w·tf/B 1.061}, corpo {tf 3, len/avg 0.3397, w·tf/B 5.943}, codigo {tf 3, len/avg 0.5215, w·tf/B 4.679}}  tf~ 11.68  n 2239  idf 4.79  parcela 9.556
     · palavra plugin  campos {titulo {tf 1, len/avg 0.9237, w·tf/B 1.061}, corpo {tf 2, len/avg 0.3397, w·tf/B 3.962}, codigo {tf 4, len/avg 0.5215, w·tf/B 6.239}}  tf~ 11.26  n 3407  idf 4.157  parcela 8.264
4. 25.7780  exploit-db  WordPress Plugin Donation 1.0 - SQL Injection
     · palavra sql  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 1.185}, corpo {tf 1, len/avg 0.2912, w·tf/B 2.135}, codigo {tf 1, len/avg 0.2391, w·tf/B 2.329}}  tf~ 5.649  n 10548  idf 2.346  parcela 4.257
     · palavra inject  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 1.185}, corpo {tf 1, len/avg 0.2912, w·tf/B 2.135}, codigo {tf 1, len/avg 0.2391, w·tf/B 2.329}}  tf~ 5.649  n 14907  idf 1.725  parcela 3.13
     · palavra wordpress  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 1.185}, corpo {tf 2, len/avg 0.2912, w·tf/B 4.27}, codigo {tf 5, len/avg 0.2391, w·tf/B 11.65}}  tf~ 17.1  n 2239  idf 4.79  parcela 9.846
     · palavra plugin  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 1.185}, corpo {tf 2, len/avg 0.2912, w·tf/B 4.27}, codigo {tf 5, len/avg 0.2391, w·tf/B 11.65}}  tf~ 17.1  n 3407  idf 4.157  parcela 8.545
5. 25.7680  exploit-db  WordPress Plugin Calculated Fields Form 1.0.10 - SQL Injection
     · palavra sql  campos {titulo {tf 1, len/avg 1.056, w·tf/B 0.9599}, corpo {tf 1, len/avg 0.3074, w·tf/B 2.081}, codigo {tf 4, len/avg 0.4555, w·tf/B 6.761}}  tf~ 9.802  n 10548  idf 2.346  parcela 4.598
     · palavra inject  campos {titulo {tf 1, len/avg 1.056, w·tf/B 0.9599}, corpo {tf 1, len/avg 0.3074, w·tf/B 2.081}, codigo {tf 2, len/avg 0.4555, w·tf/B 3.381}}  tf~ 6.421  n 14907  idf 1.725  parcela 3.197
     · palavra wordpress  campos {titulo {tf 1, len/avg 1.056, w·tf/B 0.9599}, corpo {tf 2, len/avg 0.3074, w·tf/B 4.162}, codigo {tf 4, len/avg 0.4555, w·tf/B 6.761}}  tf~ 11.88  n 2239  idf 4.79  parcela 9.571
     · palavra plugin  campos {titulo {tf 1, len/avg 1.056, w·tf/B 0.9599}, corpo {tf 2, len/avg 0.3074, w·tf/B 4.162}, codigo {tf 5, len/avg 0.4555, w·tf/B 8.451}}  tf~ 13.57  n 3407  idf 4.157  parcela 8.402
```

### BM25F com peso do título 5

`python ranquear.py "sql injection wordpress plugin" --modelo bm25f peso_titulo=5 -k 5 --explicar`

```
1. 26.6854  exploit-db  WordPress Plugin Donation 1.0 - SQL Injection
     · palavra sql  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 5.925}, corpo {tf 1, len/avg 0.2912, w·tf/B 2.135}, codigo {tf 1, len/avg 0.2391, w·tf/B 2.329}}  tf~ 10.39  n 10548  idf 2.346  parcela 4.627
     · palavra inject  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 5.925}, corpo {tf 1, len/avg 0.2912, w·tf/B 2.135}, codigo {tf 1, len/avg 0.2391, w·tf/B 2.329}}  tf~ 10.39  n 14907  idf 1.725  parcela 3.402
     · palavra wordpress  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 5.925}, corpo {tf 2, len/avg 0.2912, w·tf/B 4.27}, codigo {tf 5, len/avg 0.2391, w·tf/B 11.65}}  tf~ 21.84  n 2239  idf 4.79  parcela 9.988
     · palavra plugin  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 5.925}, corpo {tf 2, len/avg 0.2912, w·tf/B 4.27}, codigo {tf 5, len/avg 0.2391, w·tf/B 11.65}}  tf~ 21.84  n 3407  idf 4.157  parcela 8.668
2. 26.6696  exploit-db  WordPress Plugin Glossary - SQL Injection
     · palavra sql  campos {titulo {tf 1, len/avg 0.6598, w·tf/B 6.713}, corpo {tf 1, len/avg 0.275, w·tf/B 2.192}, codigo {tf 2, len/avg 0.246, w·tf/B 4.603}}  tf~ 13.51  n 10548  idf 2.346  parcela 4.74
     · palavra inject  campos {titulo {tf 1, len/avg 0.6598, w·tf/B 6.713}, corpo {tf 1, len/avg 0.275, w·tf/B 2.192}, codigo {tf 2, len/avg 0.246, w·tf/B 4.603}}  tf~ 13.51  n 14907  idf 1.725  parcela 3.485
     · palavra wordpress  campos {titulo {tf 1, len/avg 0.6598, w·tf/B 6.713}, corpo {tf 2, len/avg 0.275, w·tf/B 4.383}, codigo {tf 4, len/avg 0.246, w·tf/B 9.207}}  tf~ 20.3  n 2239  idf 4.79  parcela 9.949
     · palavra plugin  campos {titulo {tf 1, len/avg 0.6598, w·tf/B 6.713}, corpo {tf 2, len/avg 0.275, w·tf/B 4.383}, codigo {tf 2, len/avg 0.246, w·tf/B 4.603}}  tf~ 15.7  n 3407  idf 4.157  parcela 8.495
3. 26.6688  exploit-db  WordPress Plugin Ocim MP3 - SQL Injection
     · palavra sql  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 5.925}, corpo {tf 1, len/avg 0.2831, w·tf/B 2.163}, codigo {tf 3, len/avg 0.1868, w·tf/B 7.691}}  tf~ 15.78  n 10548  idf 2.346  parcela 4.797
     · palavra inject  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 5.925}, corpo {tf 1, len/avg 0.2831, w·tf/B 2.163}, codigo {tf 3, len/avg 0.1868, w·tf/B 7.691}}  tf~ 15.78  n 14907  idf 1.725  parcela 3.526
     · palavra wordpress  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 5.925}, corpo {tf 2, len/avg 0.2831, w·tf/B 4.326}, codigo {tf 2, len/avg 0.1868, w·tf/B 5.127}}  tf~ 15.38  n 2239  idf 4.79  parcela 9.775
     · palavra plugin  campos {titulo {tf 1, len/avg 0.7918, w·tf/B 5.925}, corpo {tf 2, len/avg 0.2831, w·tf/B 4.326}, codigo {tf 3, len/avg 0.1868, w·tf/B 7.691}}  tf~ 17.94  n 3407  idf 4.157  parcela 8.571
4. 26.6387  exploit-db  WordPress Plugin Another WordPress Classifieds Plugin - SQL Injection
     · palavra sql  campos {titulo {tf 1, len/avg 1.056, w·tf/B 4.8}, corpo {tf 1, len/avg 0.3236, w·tf/B 2.03}, codigo {tf 3, len/avg 0.6195, w·tf/B 4.198}}  tf~ 11.03  n 10548  idf 2.346  parcela 4.655
     · palavra inject  campos {titulo {tf 1, len/avg 1.056, w·tf/B 4.8}, corpo {tf 1, len/avg 0.3236, w·tf/B 2.03}, codigo {tf 3, len/avg 0.6195, w·tf/B 4.198}}  tf~ 11.03  n 14907  idf 1.725  parcela 3.422
     · palavra wordpress  campos {titulo {tf 2, len/avg 1.056, w·tf/B 9.599}, corpo {tf 3, len/avg 0.3236, w·tf/B 6.089}, codigo {tf 3, len/avg 0.6195, w·tf/B 4.198}}  tf~ 19.89  n 2239  idf 4.79  parcela 9.938
     · palavra plugin  campos {titulo {tf 2, len/avg 1.056, w·tf/B 9.599}, corpo {tf 3, len/avg 0.3236, w·tf/B 6.089}, codigo {tf 3, len/avg 0.6195, w·tf/B 4.198}}  tf~ 19.89  n 3407  idf 4.157  parcela 8.624
5. 26.6047  exploit-db  WordPress Plugin Booking Calendar 8.4.3 - (Authenticated) SQL Injection
     · palavra sql  campos {titulo {tf 1, len/avg 1.056, w·tf/B 4.8}, corpo {tf 2, len/avg 0.3074, w·tf/B 4.162}, codigo {tf 7, len/avg 0.7493, w·tf/B 8.621}}  tf~ 17.58  n 10548  idf 2.346  parcela 4.832
     · palavra inject  campos {titulo {tf 1, len/avg 1.056, w·tf/B 4.8}, corpo {tf 2, len/avg 0.3074, w·tf/B 4.162}, codigo {tf 8, len/avg 0.7493, w·tf/B 9.853}}  tf~ 18.81  n 14907  idf 1.725  parcela 3.567
     · palavra wordpress  campos {titulo {tf 1, len/avg 1.056, w·tf/B 4.8}, corpo {tf 1, len/avg 0.3074, w·tf/B 2.081}, codigo {tf 8, len/avg 0.7493, w·tf/B 9.853}}  tf~ 16.73  n 2239  idf 4.79  parcela 9.832
     · palavra plugin  campos {titulo {tf 1, len/avg 1.056, w·tf/B 4.8}, corpo {tf 1, len/avg 0.3074, w·tf/B 2.081}, codigo {tf 5, len/avg 0.7493, w·tf/B 6.158}}  tf~ 13.04  n 3407  idf 4.157  parcela 8.374
```
