# 플레이어 저장 레코드의 직접 접근 후보

`U1.VARS`의 458바이트는 게임 중 `$7E6D–$8036`에 놓인다. 이 지도는 Ghidra가 **명령 후보**로 해석한 코드의 직접 메모리 읽기·쓰기 참조만 모은 것이다. 인덱스 주소 지정으로 뒷부분 배열을 순회하거나 간접 포인터로 접근하는 경우는 여기에 주소별로 나타나지 않는다. 후보 참조가 실제 실행된다는 뜻도 아니다. 확인된 의미와 저장 왕복은 [레코드 형식](../disasm/U1.VARS.md), [플레이어 상태](player-state.md)에서 따로 본다.

직접 참조 후보는 **347곳**, 서로 다른 레코드 주소는 **61곳**이다. 137바이트 접두부 `$7E6D–$7EF5` 중 직접 참조된 주소는 **60곳**이다. `MI.U1, GEN, OUT, CAS, TWN, DNG, SPA, TM`의 8개 게임 단계/공용 프로그램에서 추출했다.

| 프로그램 | 직접 참조 후보 수 |
| --- | ---: |
| `MI.U1` | 29 |
| `GEN` | 30 |
| `OUT` | 104 |
| `CAS` | 35 |
| `TWN` | 24 |
| `DNG` | 46 |
| `SPA` | 38 |
| `TM` | 41 |

접근 종류: 읽기 235, 쓰기 87, 읽기·쓰기 25. 주소별 칸의 `R/W/RW`는 Ghidra 참조 유형이다. 괄호는 명령 주소이며 각 모듈·접근 종류에서 앞의 세 곳만 표시한다.

| 레코드 주소 | 현재 필드 해석 | 직접 접근 후보 |
| --- | --- | --- |
| `$7E6D` | record header | `GEN` W($8A5E) |
| `$7E6F` | world segment index 0..3, static | `OUT` R($94C1,$9503); `OUT` W($94C6); `OUT` RW($9496,$949F,$94A8 +3); `CAS` R($8977,$897A); `DNG` R($8C71) |
| `$7E70` | world bits = index << 6, static | `OUT` R($9517,$975B,$993E +4); `OUT` W($9509) |
| `$7E71` | unclassified prefix | `GEN` R($8A97) |
| `$7E72` | unclassified prefix | `GEN` R($8AA0) |
| `$7E73` | outdoor return position | `OUT` R($8956); `OUT` W($8EFE,$90CC,$92CE); `DNG` R($8C63) |
| `$7E74` | outdoor return position | `OUT` R($895B); `OUT` W($8F01,$90CF,$92D1); `DNG` R($8C6C) |
| `$7E75` | gems | `OUT` R($8D73) |
| `$7E76` | gems | `OUT` R($8D78) |
| `$7E77` | gems | `OUT` R($8D7D) |
| `$7E78` | gems | `OUT` R($8D82) |
| `$7E79` | unclassified prefix | `OUT` R($8F22,$8F8C); `OUT` W($8A1A); `DNG` R($90C5); `TM` R($91FE,$9235,$925F +1) |
| `$7E7A` | attack damage input, partial | `OUT` W($8A17); `CAS` R($8D4A,$8D4D,$8D50 +1); `TWN` R($A0F6); `DNG` R($9B55) |
| `$7E7B` | guard hit input, partial | `OUT` W($8A14); `CAS` R($995B,$995E,$9961 +5); `DNG` R($9A3C,$9A3F,$9A42 +6) |
| `$7E7C` | unclassified prefix | `OUT` R($89FC,$8CF0,$8D64 +13); `OUT` W($8A01,$8D42,$934D +2); `SPA` R($8F4C,$9D9E) |
| `$7E84` | unclassified prefix | `DNG` R($9B50); `DNG` RW($9B5A) |
| `$7E85` | unclassified prefix | `DNG` R($9B50); `DNG` RW($9B5A) |
| `$7E87` | unclassified prefix | `DNG` R($8ECE); `DNG` RW($8ED3) |
| `$7E91` | unclassified prefix | `OUT` W($8A0E); `CAS` R($9A5B); `CAS` RW($9A65); `TWN` R($A0F1); `TWN` RW($A0FB) |
| `$7E92` | unclassified prefix | `OUT` W($8A0E); `CAS` R($9A5B); `CAS` RW($9A65); `TWN` R($A0F1); `TWN` RW($A0FB) |
| `$7EA7` | unclassified prefix | `OUT` W($959B) |
| `$7EA8` | craft creation gate, partial | `OUT` R($956C); `OUT` W($959B); `OUT` RW($95CB) |
| `$7EB1` | unclassified prefix | `OUT` R($9533); `OUT` W($9116) |
| `$7EB2` | unclassified prefix | `OUT` R($953E); `OUT` W($911E) |
| `$7EB3` | unclassified prefix | `OUT` R($9549); `OUT` W($9126,$955E) |
| `$7EB4` | unclassified prefix | `OUT` R($9554); `OUT` W($912E,$955E) |
| `$7EB5` | craft request | `OUT` R($9567); `OUT` W($9593) |
| `$7EB7` | sex | `GEN` W($8D80); `TWN` R($895E) |
| `$7EB8` | name | `MI.U1` R($8839) |
| `$7EB9` | name | `MI.U1` R($8839) |
| `$7EC6` | HP | `MI.U1` R($8382); `MI.U1` W($889B); `OUT` R($898D,$89A4,$8A40); `OUT` RW($8A3A); `CAS` R($8A31,$99CB); `CAS` W($99D1); `TWN` R($8A28); `DNG` R($8DE9,$9B05); `DNG` W($9B0C); `TM` R($8E75,$9526,$99BF) |
| `$7EC7` | HP | `MI.U1` R($837F); `MI.U1` W($889E); `OUT` R($8990,$89A7); `CAS` R($8A34,$998F,$99D4); `CAS` W($99D9); `TWN` R($8A2B); `DNG` R($8DEC,$9B0F); `DNG` W($9B15); `TM` R($8E78,$9520,$99C4) |
| `$7EC8` | attributes | `GEN` R($8D1F,$8D33,$8E19); `GEN` W($8D25,$8D39,$8E1F); `CAS` R($8D46) |
| `$7ECA` | attributes | `GEN` R($8D10,$8E22,$8E4B); `GEN` W($8D16,$8E28,$8E51); `CAS` R($8D1B) |
| `$7ECC` | attributes | `CAS` R($9956); `DNG` R($9A37) |
| `$7ED0` | attributes | `GEN` R($8D2A,$8E31); `GEN` W($8D30,$8E37); `CAS` R($9A70); `TWN` R($A106) |
| `$7ED2` | attributes | `GEN` R($8D01,$8E40); `GEN` W($8D07,$8E46); `TWN` R($9259); `TM` R($928C) |
| `$7ED4` | Coin | `MI.U1` R($83A0); `MI.U1` W($888F); `TWN` R($932F,$933E); `TWN` W($9344); `DNG` R($950D,$9520); `DNG` W($9514,$952E); `SPA` R($A1B1) |
| `$7ED5` | Coin | `MI.U1` R($839D); `MI.U1` W($8892); `TWN` R($9334,$9347); `TWN` W($934C); `DNG` R($9517,$9525); `DNG` W($951D,$9533); `SPA` R($A1AE) |
| `$7ED6` | race | `GEN` R($8CFA); `GEN` W($8CDE) |
| `$7ED8` | class | `GEN` R($8E12); `GEN` W($8DF8); `CAS` R($91A4); `TWN` R($8FBB); `TM` R($9267) |
| `$7EDA` | shared turn/accounting byte | `MI.U1` R($8313); `MI.U1` W($8319) |
| `$7EDB` | unclassified prefix | `MI.U1` R($8324); `MI.U1` W($8329) |
| `$7EDC` | unclassified prefix | `MI.U1` R($8324); `MI.U1` W($8329) |
| `$7EE4` | shared turn/resource byte | `MI.U1` R($82F4); `MI.U1` W($82FA) |
| `$7EE5` | Food | `MI.U1` R($82FF,$8307,$838B); `MI.U1` W($8895); `MI.U1` RW($830F); `OUT` R($89AC,$8A4D); `OUT` RW($8A47); `CAS` R($8A39); `TWN` R($8A30,$934F); `TWN` W($9356); `DNG` R($8DF4); `TM` R($8E6D) |
| `$7EE6` | Food | `MI.U1` R($8302,$8388); `MI.U1` W($8898); `MI.U1` RW($830C); `OUT` R($89AF); `CAS` R($8A3C); `TWN` R($8A33,$9359); `TWN` W($935F); `DNG` R($8DF7); `TM` R($8E70) |
| `$7EE7` | SPA third resource, unresolved | `MI.U1` R($8394); `DNG` R($947F,$9491); `DNG` W($9486,$949F); `SPA` R($A1A8) |
| `$7EE8` | SPA third resource, unresolved | `MI.U1` R($8391); `OUT` R($95E2,$9665); `DNG` R($9489,$9496); `DNG` W($948E,$94A4); `SPA` R($A1A5) |
| `$7EE9` | Fuel | `SPA` R($8A70,$92DD,$95B6 +9); `SPA` W($A15C,$A16D) |
| `$7EEA` | Fuel | `SPA` R($8A73,$92E0,$95B9 +9); `SPA` W($A170); `SPA` RW($A161) |
| `$7EEB` | Shield | `SPA` R($A196) |
| `$7EEC` | Shield | `SPA` R($A193) |
| `$7EED` | unclassified prefix | `OUT` W($9A76,$9A7A); `CAS` R($896A,$8D6C,$9AFD); `TWN` R($8979); `DNG` R($8C5D) |
| `$7EEF` | unclassified prefix | `GEN` W($8E5A); `SPA` R($8956) |
| `$7EF0` | unclassified prefix | `GEN` W($8E60); `SPA` R($895B) |
| `$7EF2` | unclassified prefix | `OUT` R($9668); `OUT` W($9619,$96A8,$983F); `TM` R($8EDC,$922D,$94DB +5); `TM` W($8AE3,$9897,$9927); `TM` RW($8EE1,$9232,$94E0 +1) |
| `$7EF3` | unclassified prefix | `OUT` W($9835) |
| `$7EF4` | unclassified prefix | `TM` R($987A,$990A,$991E); `TM` W($8ADB,$987D,$990F) |
| `$7EF5` | unclassified prefix | `TM` R($9882,$9904,$9912); `TM` W($8ADE,$9885,$9917) |
| `$7EF6` | object count | `OUT` R($950C,$95AF,$95D2 +7); `OUT` RW($9954,$9996) |

이 장부는 **주소별 직접 참조의 탐색 인덱스**다. 특정 바이트에 행이 없다는 사실은 미사용을 증명하지 않는다. 다음 단계에서는 미분류 접두부의 실제 생산자·소비자, 인덱스 배열의 경계, 각 필드의 저장·재로드 효과를 명령별 실행 기록으로 교차 검증한다.
