import pandas as pd

df = pd.read_csv("train.csv")
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
df.columns = [c.strip() for c in df.columns]

# Calculate points change if columns exist
if 'nifty_before' in df.columns and 'nifty_after' in df.columns:
    df['points_change'] = df['nifty_after'] - df['nifty_before']

nifty_current = float(input("NIFTY current: "))
call_volume   = float(input("Call OI change: "))
put_volume    = float(input("Put OI change: "))
total_call    = float(input("Total Call OI: "))
total_put     = float(input("Total Put OI: "))

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
print_cols = feats + ['WINNER']
if 'points_change' in near.columns:
    print_cols += ['points_change']
print(near[print_cols])

if call_votes >= put_votes:
    print(f"\nSuggestion: BUY CALL  (history {call_votes}-{put_votes})")
    suggestion = "BUY CALL"
else:
    print(f"\nSuggestion: BUY PUT   (history {put_votes}-{call_votes})")
    suggestion = "BUY PUT"

# Expected Points Change
avg_points = 0
if 'points_change' in near.columns:
    avg_points = near['points_change'].mean()
    if avg_points >= 0:
        print(f"Expected NIFTY Increase: +{avg_points:.2f} points")
    else:
        print(f"Expected NIFTY Decrease: {avg_points:.2f} points")
    print(f"Target NIFTY Price: {nifty_current + avg_points:.2f}")

# ==========================================
# REVERSE ENGINEERING ANALYSIS
# ==========================================
print("\n" + "="*60)
print("REVERSE ENGINEERING ANALYSIS")
print("="*60)

# 1. Feature Contribution Analysis
print("\n1. KEY DRIVERS OF THIS PREDICTION:")
print("-" * 60)

for f, v in zip(feats, live):
    s = df[f].std()
    if pd.isna(s) or s == 0: 
        s = 1
    
    avg_similar = near[f].mean()
    diff_percent = ((v - avg_similar) / abs(avg_similar) * 100) if avg_similar != 0 else 0
    
    print(f"   {f:15} | Live: {v:>12,.0f} | Historical Avg: {avg_similar:>12,.0f} | Diff: {diff_percent:>+6.1f}%")

# 2. PCR (Put Call Ratio) Analysis
print("\n2. PUT-CALL RATIO ANALYSIS:")
print("-" * 60)
live_pcr = total_put / total_call if total_call != 0 else 0
hist_pcr = near['total_put'].mean() / near['total_call'].mean() if near['total_call'].mean() != 0 else 0

print(f"   Live PCR:        {live_pcr:.3f}")
print(f"   Historical PCR:  {hist_pcr:.3f}")
if live_pcr > 1.2:
    print("   → Bullish Signal: More Put writing (support building)")
elif live_pcr < 0.8:
    print("   → Bearish Signal: More Call writing (resistance building)")
else:
    print("   → Neutral Signal: Balanced OI")

# 3. OI Change Analysis
print("\n3. OI CHANGE INTERPRETATION:")
print("-" * 60)
if suggestion == "BUY CALL":
    if call_volume < 0 and put_volume < 0:
        print("   ⚠ WARNING: Both Call & Put OI decreasing")
        print("   → Unwinding happening - trend may be weak")
    elif call_volume > 0:
        print("   ✓ Call OI Increasing - Fresh buying in Calls")
    if put_volume < 0:
        print("   ✓ Put OI Decreasing - Put writers covering (bullish)")
else:  # BUY PUT
    if put_volume > 0 and call_volume < 0:
        print("   ✓ Put OI Increasing - Fresh buying in Puts")
        print("   ✓ Call OI Decreasing - Call writers covering (bearish)")
    elif put_volume < 0 and call_volume < 0:
        print("   ⚠ WARNING: Both OI decreasing - Unwinding")

# 4. Risk Analysis from Historical Similar Candles
print("\n4. RISK ANALYSIS (Based on Similar Past Candles):")
print("-" * 60)
if 'points_change' in near.columns:
    wins = near[near['WINNER'].str.strip() == suggestion]['points_change']
    losses = near[near['WINNER'].str.strip() != suggestion]['points_change']
    
    if len(wins) > 0:
        avg_win = wins.mean()
        max_win = wins.max()
        min_win = wins.min()
        print(f"   When {suggestion} worked:")
        print(f"   - Average Gain:  +{avg_win:.2f} points")
        print(f"   - Best Case:     +{max_win:.2f} points")
        print(f"   - Worst Case:    {min_win:+.2f} points")
    
    if len(losses) > 0:
        avg_loss = losses.mean()
        print(f"\n   When {suggestion} FAILED:")
        print(f"   - Average Loss:  {avg_loss:+.2f} points")
        print(f"   → Consider Stop Loss: {nifty_current + avg_loss:.2f}")

# 5. Reverse Engineering: What Would Invalidate This Setup?
print("\n5. SETUP INVALIDATION CONDITIONS:")
print("-" * 60)
if suggestion == "BUY CALL":
    print("   This BUY CALL setup is INVALIDATED if:")
    print(f"   ✗ NIFTY falls below: {nifty_current - abs(avg_points):.2f} ({abs(avg_points):.0f} points SL)")
    if total_put > 0:
        print(f"   ✗ Put OI increases by >20% from current: {total_put * 1.2:,.0f}")
    print("   ✗ Call OI starts decreasing rapidly")
else:
    print("   This BUY PUT setup is INVALIDATED if:")
    print(f"   ✗ NIFTY rises above: {nifty_current + abs(avg_points):.2f} ({abs(avg_points):.0f} points SL)")
    if total_call > 0:
        print(f"   ✗ Call OI increases by >20% from current: {total_call * 1.2:,.0f}")
    print("   ✗ Put OI starts decreasing rapidly")

# 6. Optimal Entry/Exit Strategy
print("\n6. SUGGESTED TRADING STRATEGY:")
print("-" * 60)
if 'points_change' in near.columns:
    avg_gain = near[near['WINNER'].str.strip() == suggestion]['points_change'].mean() if len(near[near['WINNER'].str.strip() == suggestion]) > 0 else avg_points
    
    print(f"   Entry:        Current NIFTY {nifty_current:.2f}")
    print(f"   Target 1:     {nifty_current + (avg_gain * 0.5):.2f} (+{(avg_gain * 0.5):.0f} pts) - Book 50%")
    print(f"   Target 2:     {nifty_current + avg_gain:.2f} (+{avg_gain:.0f} pts) - Exit remaining")
    print(f"   Stop Loss:    {nifty_current - (abs(avg_gain) * 0.5):.2f} (-{abs(avg_gain) * 0.5:.0f} pts)")
    print(f"   Risk/Reward:  1:{abs(avg_gain) / (abs(avg_gain) * 0.5):.1f}")

# ==========================================
# SMART MONEY OI LOGIC CHECK
# ==========================================
print("\n" + "="*60)
print("SMART MONEY OI LOGIC CHECK")
print("="*60)

# Calculate Put-Call Ratio (PCR)
pcr = total_put / total_call if total_call != 0 else 1.0

print(f"Current Put-Call Ratio (PCR): {pcr:.2f}")

# 1. Evaluate the General Bias
if pcr > 1.1:
    print("🟢 BIAS: BULLISH (Heavy Put Writing = Strong Support)")
elif pcr < 0.8:
    print("🔴 BIAS: BEARISH (Heavy Call Writing = Strong Resistance)")
else:
    print("🟡 BIAS: NEUTRAL / SIDEWAYS (Balanced OI)")

# 2. Evaluate the OI Change (The Momentum)
print("\nOI Change Analysis:")
if call_volume > 0 and put_volume < 0:
    print("⚠️  BEARISH CONFIRMATION: Call writers are adding positions, Put writers are running away.")
elif put_volume > 0 and call_volume < 0:
    print(" BULLISH CONFIRMATION: Put writers are adding positions, Call writers are running away.")
elif call_volume > 0 and put_volume > 0:
    print("⚖️  BOTH SIDES BUILDING: A massive volatile move (breakout) is coming. Wait for direction.")
    print(f"   → If NIFTY crosses {nifty_current + 30}, expect a massive UP explosion (Call Short Covering).")
    print(f"   → If NIFTY falls below {nifty_current - 30}, expect a massive DOWN crash (Put Unwinding).")
else:
    print("📉 BOTH SIDES UNWINDING: Market is losing interest. Expect low volatility / sideways chop.")

# 3. Cross-Check with Algorithm Suggestion
print("\nLogic Cross-Check:")
if suggestion == "BUY CALL" and pcr < 0.8:
    print("⚠️  WARNING: Algorithm suggests BUY CALL, but PCR is Bearish (< 0.8).")
    print("   → This might be a 'Short Covering' breakout play. Keep Stop Loss very tight!")
elif suggestion == "BUY PUT" and pcr > 1.1:
    print("⚠️  WARNING: Algorithm suggests BUY PUT, but PCR is Bullish (> 1.1).")
    print("   → Fighting the support wall. High risk of a bounce. Keep Stop Loss very tight!")
else:
    print("✅ Algorithm suggestion aligns with Smart Money OI flow.")

print("="*60)

# ==========================================
# AUTO-SAVE TO CSV FEATURE
# ==========================================
save_data = input("\nDo you want to save these inputs to train.csv? (y/n): ").strip().lower()

if save_data == 'y':
    # Create a dictionary for the new row
    new_row = {
        'nifty_before': nifty_current,
        'call_volume': call_volume,
        'put_volume': put_volume,
        'total_call': total_call,
        'total_put': total_put,
        'WINNER': 'PENDING',
        'points_change': 0,
        'nifty_after': 0
    }
    
    # Convert to DataFrame and append to CSV
    pd.DataFrame([new_row]).to_csv('train.csv', mode='a', header=False, index=False)
    
    print("\n✅ Successfully saved to train.csv!")
    print("⚠️  Remember to update the 'WINNER' and 'points_change' columns later once the candle closes.")
else:
    print("\nData not saved.")

print("\n" + "="*60)
print("END OF ANALYSIS")
print("="*60)