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

# ==========================================
# PRIMARY SIGNAL: OI CHANGE LOGIC
# ==========================================
# This is the CORE rule: Follow the option writers
if put_volume > call_volume:
    oi_signal = "BUY CALL"
    oi_reason = f"Put OI increasing more (+{put_volume:,} vs +{call_volume:,}) → Put writers bullish"
else:
    oi_signal = "BUY PUT"
    oi_reason = f"Call OI increasing more (+{call_volume:,} vs +{put_volume:,}) → Call writers bearish"

print(f"\n{'='*60}")
print(f"PRIMARY OI SIGNAL: {oi_signal}")
print(f"Reason: {oi_reason}")
print(f"{'='*60}")

# ==========================================
# SECONDARY SIGNAL: KNN PATTERN MATCHING
# ==========================================
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
    knn_signal = "BUY CALL"
    print(f"\nKNN Pattern Signal: BUY CALL  (history {call_votes}-{put_votes})")
else:
    knn_signal = "BUY PUT"
    print(f"\nKNN Pattern Signal: BUY PUT   (history {put_votes}-{call_votes})")

# ==========================================
# FINAL DECISION: Combine Both Signals
# ==========================================
print("\n" + "="*60)
print("FINAL DECISION LOGIC")
print("="*60)

if oi_signal == knn_signal:
    # Both agree - HIGH CONFIDENCE
    final_suggestion = oi_signal
    confidence = "HIGH"
    print(f"\n✅ BOTH SIGNALS AGREE: {final_suggestion}")
    print(f"   Confidence: {confidence}")
else:
    # Conflict - Use OI logic as primary (it's real-time)
    final_suggestion = oi_signal
    confidence = "MEDIUM"
    print(f"\n⚠️  SIGNAL CONFLICT DETECTED:")
    print(f"   - OI Flow says:    {oi_signal} (Real-time smart money)")
    print(f"   - KNN Pattern says: {knn_signal} (Historical pattern)")
    print(f"\n   → Going with OI Flow (Primary Signal)")
    print(f"   Confidence: {confidence} (Conflicting signals)")

suggestion = final_suggestion

# Expected Points Change
avg_points = 0
if 'points_change' in near.columns:
    avg_points = near['points_change'].mean()
    if avg_points >= 0:
        print(f"\nExpected NIFTY Increase: +{avg_points:.2f} points")
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

# 3. OI Change Analysis - THE CORE LOGIC
print("\n3. OI CHANGE INTERPRETATION (CORE LOGIC):")
print("-" * 60)

oi_diff = put_volume - call_volume
if oi_diff > 0:
    print(f"   ✅ Net OI Flow: +{oi_diff:,} (Put side stronger)")
    print("   → Put writers are MORE aggressive than Call writers")
    print("   → This creates SUPPORT → Market likely to go UP")
    print("   → Signal: BUY CALL")
else:
    print(f"   ✅ Net OI Flow: {oi_diff:,} (Call side stronger)")
    print("   → Call writers are MORE aggressive than Put writers")
    print("   → This creates RESISTANCE → Market likely to go DOWN")
    print("   → Signal: BUY PUT")

# Additional OI context
if call_volume > 0 and put_volume > 0:
    print("\n   📊 Both sides adding OI:")
    if abs(oi_diff) < min(abs(call_volume), abs(put_volume)) * 0.3:
        print("   → Close competition - High volatility expected")
    else:
        print("   → Clear winner - Directional move likely")
elif call_volume < 0 and put_volume < 0:
    print("\n   ⚠️  Both sides unwinding - Trend weakening")

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

# 5. Setup Invalidation Conditions
print("\n5. SETUP INVALIDATION CONDITIONS:")
print("-" * 60)
if suggestion == "BUY CALL":
    print("   This BUY CALL setup is INVALIDATED if:")
    print(f"   ✗ NIFTY falls below: {nifty_current - abs(avg_points):.2f} ({abs(avg_points):.0f} points SL)")
    if total_put > 0:
        print(f"   ✗ Put OI stops increasing or decreases")
        print(f"   ✗ Call OI increases by >20% from current: {total_call * 1.2:,.0f}")
else:
    print("   This BUY PUT setup is INVALIDATED if:")
    print(f"   ✗ NIFTY rises above: {nifty_current + abs(avg_points):.2f} ({abs(avg_points):.0f} points SL)")
    if total_call > 0:
        print(f"   ✗ Call OI stops increasing or decreases")
        print(f"   ✗ Put OI increases by >20% from current: {total_put * 1.2:,.0f}")

# 6. Optimal Entry/Exit Strategy
print("\n6. SUGGESTED TRADING STRATEGY:")
print("-" * 60)
if 'points_change' in near.columns:
    avg_gain = near[near['WINNER'].str.strip() == suggestion]['points_change'].mean() if len(near[near['WINNER'].str.strip() == suggestion]) > 0 else abs(avg_points)
    
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

# 2. Evaluate the OI Change (The Momentum) - THIS IS THE KEY
print("\nOI Change Momentum Analysis:")
if put_volume > call_volume and put_volume > 0:
    print(" BULLISH MOMENTUM: Put writers adding MORE than Call writers")
    print("   → Smart money expects market to stay UP")
elif call_volume > put_volume and call_volume > 0:
    print("️  BEARISH MOMENTUM: Call writers adding MORE than Put writers")
    print("   → Smart money expects market to stay DOWN")
elif call_volume > 0 and put_volume > 0:
    print("⚖️  BOTH SIDES BUILDING: A massive volatile move (breakout) is coming.")
    if abs(put_volume - call_volume) < min(put_volume, call_volume) * 0.2:
        print("   → Very close battle - Wait for price breakout confirmation")
        print(f"   → If NIFTY crosses {nifty_current + 30}, expect massive UP (Call Short Covering)")
        print(f"   → If NIFTY falls below {nifty_current - 30}, expect massive DOWN (Put Unwinding)")
else:
    print("📉 BOTH SIDES UNWINDING: Market losing interest. Expect sideways chop.")

# 3. Cross-Check with Algorithm Suggestion
print("\nSignal Validation:")
if oi_signal == knn_signal:
    print("✅ PERFECT ALIGNMENT: OI Flow + Historical Pattern agree")
    print("   → High probability setup")
else:
    print("⚠️  SIGNAL DIVERGENCE:")
    print(f"   - Real-time OI says: {oi_signal}")
    print(f"   - Historical KNN says: {knn_signal}")
    print("   → Trusting OI Flow (real-time smart money action)")
    print("   → Reduce position size due to conflicting signals")

print("="*60)

# ==========================================
# AUTO-SAVE TO CSV FEATURE
# ==========================================
save_data = input("\nDo you want to save these inputs to train.csv? (y/n): ").strip().lower()

if save_data == 'y':
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
    
    pd.DataFrame([new_row]).to_csv('train.csv', mode='a', header=False, index=False)
    
    print("\n✅ Successfully saved to train.csv!")
    print("⚠️  Remember to update the 'WINNER' and 'points_change' columns later.")
else:
    print("\nData not saved.")

print("\n" + "="*60)
print("END OF ANALYSIS")
print("="*60)