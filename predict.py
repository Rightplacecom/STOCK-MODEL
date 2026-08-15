import pandas as pd

df = pd.read_csv("train.csv")
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
df.columns = [c.strip() for c in df.columns]

nifty_current = float(input("NIFTY current: "))
call_volume  = float(input("Call OI change: "))
put_volume   = float(input("Put OI change: "))
total_call   = float(input("Total Call OI: "))
total_put    = float(input("Total Put OI: "))

feats = ['call_volume', 'put_volume', 'total_call', 'total_put']
live  = [call_volume, put_volume, total_call, total_put]

dist = 0
for f, v in zip(feats, live):
    s = df[f].std()
    if pd.isna(s) or s == 0:
        s = 1
    dist = dist + ((df[f] - v) / s) ** 2
df['distance'] = dist ** 0.5

near = df.nsmallest(3, 'distance')
call_votes = (near['WINNER'].str.strip() == 'BUY CALL').sum()
put_votes  = (near['WINNER'].str.strip() == 'BUY PUT').sum()

print("\nSimilar past candles:")
print(near[feats + ['WINNER']])

if call_votes >= put_votes:
    print(f"\nSuggestion: BUY CALL  (history {call_votes}-{put_votes})")
else:
    print(f"\nSuggestion: BUY PUT   (history {put_votes}-{call_votes})")