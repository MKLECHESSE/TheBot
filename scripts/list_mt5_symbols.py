import MetaTrader5 as mt5

if not mt5.initialize():
    print('Failed to initialize MT5')
    raise SystemExit(1)

syms = mt5.symbols_get()
print('total symbols =', len(syms))
names = [s.name for s in syms]

for cur in ("EUR","GBP","USD","JPY","AUD","XAU","BTC"):
    matches = [n for n in names if cur.lower() in n.lower()]
    print(f"{cur} matches: {matches[:20]}")

print('\nSample symbols (first 80):')
print(names[:80])

mt5.shutdown()
