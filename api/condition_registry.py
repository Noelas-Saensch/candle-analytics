"""Central registry of all conditions, indicators, metrics by category/subcategory.

Used by /api/conditions/search endpoint and the Strategy Lab frontend
for search-as-you-type condition input.

Dynamically extended with custom_types/ registry (orders, indicators,
conditions, CDL patterns).
"""

import sys
from pathlib import Path

# Load custom types registry
_custom_dir = Path(__file__).parent.parent / "custom_types"
if _custom_dir.exists():
    sys.path.insert(0, str(_custom_dir.parent))
    try:
        from custom_types.registry import (
            flatten_custom_for_registry,
            get_order_type_definitions,
            search_custom_conditions,
            get_condition_template,
            export_full_catalog,
            save_custom_indicators,
        )
        _CUSTOM_ENTRIES = flatten_custom_for_registry()
    except Exception as e:
        print(f"[condition_registry] Custom types load warning: {e}")
        _CUSTOM_ENTRIES = []
else:
    _CUSTOM_ENTRIES = []

CONDITION_REGISTRY = {
    "ohlcv_metrics": {
        "id": "ohlcv_metrics",
        "label": "OHLCV Metrics",
        "description": "Raw OHLCV-derived percentage metrics computed at candle close",
        "icon": "📊",
        "subcategories": {
            "threshold": {
                "id": "threshold",
                "label": "Threshold",
                "description": "Direct metric comparison (metric > value)",
                "metrics": {
                    "oc": {
                        "id": "oc",
                        "label": "OC%",
                        "description": "(close - open) / open * 100 — body size as % of open",
                        "unit": "%",
                        "default_op": "gt",
                        "default_value": 0.5,
                        "ops": ["gt", "gte", "lt", "lte", "eq", "neq"],
                    },
                    "oh": {
                        "id": "oh",
                        "label": "OH%",
                        "description": "(high - open) / open * 100 — upside wick as % of open",
                        "unit": "%",
                        "default_op": "gt",
                        "default_value": 1.0,
                        "ops": ["gt", "gte", "lt", "lte", "eq", "neq"],
                    },
                    "ol": {
                        "id": "ol",
                        "label": "OL%",
                        "description": "(low - open) / open * 100 — downside wick as % of open",
                        "unit": "%",
                        "default_op": "lt",
                        "default_value": -1.0,
                        "ops": ["gt", "gte", "lt", "lte", "eq", "neq"],
                    },
                    "hl": {
                        "id": "hl",
                        "label": "HL%",
                        "description": "(high - low) / open * 100 — total range as % of open",
                        "unit": "%",
                        "default_op": "gt",
                        "default_value": 2.0,
                        "ops": ["gt", "gte", "lt", "lte", "eq", "neq"],
                    },
                    "hc": {
                        "id": "hc",
                        "label": "HC%",
                        "description": "(high - close) / open * 100 — close-to-high distance as % of open",
                        "unit": "%",
                        "default_op": "lt",
                        "default_value": 0.5,
                        "ops": ["gt", "gte", "lt", "lte", "eq", "neq"],
                    },
                    "lc": {
                        "id": "lc",
                        "label": "LC%",
                        "description": "(low - close) / open * 100 — close-to-low distance as % of open",
                        "unit": "%",
                        "default_op": "gt",
                        "default_value": -0.5,
                        "ops": ["gt", "gte", "lt", "lte", "eq", "neq"],
                    },
                    "vol": {
                        "id": "vol",
                        "label": "Vol%",
                        "description": "volume / max_volume * 100 — relative volume",
                        "unit": "%",
                        "default_op": "gt",
                        "default_value": 50,
                        "ops": ["gt", "gte", "lt", "lte", "eq", "neq"],
                    },
                },
            },
            "pctl": {
                "id": "pctl",
                "label": "Percentile",
                "description": "Percentile rank of a metric (metric pctl N = top N%)",
                "metrics": {},
                "default_op": "gte",
                "default_value": 80,
                "ops": ["gte", "gt", "lte", "lt"],
            },
        },
    },
    "trend_indicators": {
        "id": "trend_indicators",
        "label": "Trend Indicators",
        "description": "Directional movement and trend-following indicators",
        "icon": "📈",
        "subcategories": {
            "moving_averages": {
                "id": "moving_averages",
                "label": "Moving Averages",
                "description": "SMA, EMA, WEMA — trend direction and dynamic support/resistance",
                "indicators": {
                    "sma": {
                        "id": "sma",
                        "label": "SMA",
                        "description": "Simple Moving Average — mean of last N closes",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}],
                        "outputs": [{"name": "value", "label": "SMA value"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below", "crossover", "crossunder"],
                    },
                    "ema": {
                        "id": "ema",
                        "label": "EMA",
                        "description": "Exponential Moving Average — weighted mean, more weight to recent prices",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}],
                        "outputs": [{"name": "value", "label": "EMA value"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below", "crossover", "crossunder"],
                    },
                    "wema": {
                        "id": "wema",
                        "label": "WEMA",
                        "description": "Weighted Exponential Moving Average — enhanced EMA with volume weighting",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}],
                        "outputs": [{"name": "value", "label": "WEMA value"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below", "crossover", "crossunder"],
                    },
                    "hma": {
                        "id": "hma",
                        "label": "HMA",
                        "description": "Hull Moving Average — smooth and responsive moving average with minimal lag",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}],
                        "outputs": [{"name": "value", "label": "HMA value"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below", "crossover", "crossunder"],
                    },
                },
            },
            "macd": {
                "id": "macd",
                "label": "MACD",
                "description": "Moving Average Convergence Divergence — trend direction and momentum shifts",
                "indicators": {
                    "macd": {
                        "id": "macd",
                        "label": "MACD",
                        "description": "MACD line, signal line, histogram — trend momentum and crossovers",
                        "params": [
                            {"name": "fast", "label": "Fast period", "type": "int", "default": 12, "min": 2, "max": 100, "step": 1},
                            {"name": "slow", "label": "Slow period", "type": "int", "default": 26, "min": 2, "max": 200, "step": 1},
                            {"name": "signal", "label": "Signal period", "type": "int", "default": 9, "min": 2, "max": 100, "step": 1},
                        ],
                        "outputs": [
                            {"name": "macd_line", "label": "MACD line"},
                            {"name": "signal_line", "label": "Signal line"},
                            {"name": "histogram", "label": "Histogram"},
                        ],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["line_above_signal", "line_below_signal", "crossover", "crossunder", "histogram_positive", "histogram_negative"],
                    },
                },
            },
            "adx": {
                "id": "adx",
                "label": "ADX / DMI",
                "description": "Average Directional Index — trend strength indicator",
                "indicators": {
                    "adx": {
                        "id": "adx",
                        "label": "ADX",
                        "description": "Average Directional Index — measures trend strength (25+ = strong trend)",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 14, "min": 2, "max": 100, "step": 1}],
                        "outputs": [{"name": "value", "label": "ADX"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                    },
                    "di_plus": {
                        "id": "di_plus",
                        "label": "DI+",
                        "description": "Positive Directional Indicator — upward trend pressure",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 14, "min": 2, "max": 100, "step": 1}],
                        "outputs": [{"name": "value", "label": "DI+"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["above_di_minus", "below_di_minus"],
                    },
                    "di_minus": {
                        "id": "di_minus",
                        "label": "DI-",
                        "description": "Negative Directional Indicator — downward trend pressure",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 14, "min": 2, "max": 100, "step": 1}],
                        "outputs": [{"name": "value", "label": "DI-"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["above_di_plus", "below_di_plus"],
                    },
                },
            },
            "parabolic_sar": {
                "id": "parabolic_sar",
                "label": "Parabolic SAR",
                "description": "Parabolic Stop and Reverse — trend direction and reversal points",
                "indicators": {
                    "psar": {
                        "id": "psar",
                        "label": "PSAR",
                        "description": "Parabolic SAR — dots above/below price indicate trend direction",
                        "params": [
                            {"name": "acceleration", "label": "Acceleration", "type": "float", "default": 0.02, "min": 0.001, "max": 0.5, "step": 0.005},
                            {"name": "max_acceleration", "label": "Max acceleration", "type": "float", "default": 0.2, "min": 0.01, "max": 1.0, "step": 0.01},
                        ],
                        "outputs": [{"name": "value", "label": "PSAR value"}],
                        "ops": ["gt", "lt"],
                        "comparisons": ["price_above", "price_below"],
                    },
                },
            },
            "ichimoku": {
                "id": "ichimoku",
                "label": "Ichimoku Cloud",
                "description": "Ichimoku Kinko Hyo — support/resistance, trend direction, and momentum at a glance",
                "indicators": {
                    "ichimoku_tenkan_9": {
                        "id": "ichimoku_tenkan_9",
                        "label": "Tenkan-sen (9)",
                        "description": "Conversion Line — (highest high + lowest low)/2 over 9 periods. Short-term trend indicator.",
                        "params": [],
                        "outputs": [{"name": "value", "label": "Tenkan value"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below", "crossover", "crossunder"],
                    },
                    "ichimoku_kijun_26": {
                        "id": "ichimoku_kijun_26",
                        "label": "Kijun-sen (26)",
                        "description": "Base Line — (highest high + lowest low)/2 over 26 periods. Medium-term trend indicator.",
                        "params": [],
                        "outputs": [{"name": "value", "label": "Kijun value"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below", "crossover", "crossunder"],
                    },
                    "ichimoku_senkou_a": {
                        "id": "ichimoku_senkou_a",
                        "label": "Senkou Span A",
                        "description": "Leading Span A — (Tenkan + Kijun)/2. Cloud edge, forward-looking support/resistance.",
                        "params": [],
                        "outputs": [{"name": "value", "label": "Senkou A value"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below"],
                    },
                    "ichimoku_senkou_b": {
                        "id": "ichimoku_senkou_b",
                        "label": "Senkou Span B",
                        "description": "Leading Span B — (highest high + lowest low)/2 over 52 periods. Cloud edge, stronger support/resistance.",
                        "params": [],
                        "outputs": [{"name": "value", "label": "Senkou B value"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below"],
                    },
                    "ichimoku_chikou_26": {
                        "id": "ichimoku_chikou_26",
                        "label": "Chikou Span (26)",
                        "description": "Lagging Span — close shifted 26 bars back. Confirms trend when above/below price.",
                        "params": [],
                        "outputs": [{"name": "value", "label": "Chikou value"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below"],
                    },
                },
            },
        },
    },
    "momentum_indicators": {
        "id": "momentum_indicators",
        "label": "Momentum Indicators",
        "description": "Rate of change and oscillator indicators for overbought/oversold conditions",
        "icon": "⚡",
        "subcategories": {
            "rsi": {
                "id": "rsi",
                "label": "RSI",
                "description": "Relative Strength Index — overbought/oversold oscillator (0-100)",
                "indicators": {
                    "rsi": {
                        "id": "rsi",
                        "label": "RSI",
                        "description": "Relative Strength Index — values above 70 = overbought, below 30 = oversold",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 14, "min": 2, "max": 100, "step": 1}],
                        "outputs": [{"name": "value", "label": "RSI"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "default_op": "lt",
                        "default_value": 30,
                        "presets": [
                            {"label": "Oversold (< 30)", "op": "lt", "value": 30},
                            {"label": "Overbought (> 70)", "op": "gt", "value": 70},
                            {"label": "Extreme oversold (< 20)", "op": "lt", "value": 20},
                            {"label": "Extreme overbought (> 80)", "op": "gt", "value": 80},
                            {"label": "Bullish zone (> 50)", "op": "gt", "value": 50},
                            {"label": "Bearish zone (< 50)", "op": "lt", "value": 50},
                        ],
                    },
                },
            },
            "stochastic": {
                "id": "stochastic",
                "label": "Stochastic",
                "description": "Stochastic Oscillator — %K and %D lines for overbought/oversold",
                "indicators": {
                    "stoch_k": {
                        "id": "stoch_k",
                        "label": "Stochastic %K",
                        "description": "Fast stochastic %K line — raw oscillator value",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 14, "min": 2, "max": 100, "step": 1}],
                        "outputs": [{"name": "value", "label": "%K"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "presets": [
                            {"label": "Oversold (< 20)", "op": "lt", "value": 20},
                            {"label": "Overbought (> 80)", "op": "gt", "value": 80},
                        ],
                    },
                    "stoch_d": {
                        "id": "stoch_d",
                        "label": "Stochastic %D",
                        "description": "Slow stochastic %D line — smoothed %K (3-period SMA)",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 14, "min": 2, "max": 100, "step": 1}],
                        "outputs": [{"name": "value", "label": "%D"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["k_above_d", "k_below_d", "k_crossover_d", "k_crossunder_d"],
                    },
                },
            },
            "williams_r": {
                "id": "williams_r",
                "label": "Williams %R",
                "description": "Williams Percent Range — overbought/oversold (-100 to 0)",
                "indicators": {
                    "williams_r": {
                        "id": "williams_r",
                        "label": "Williams %R",
                        "description": "Values below -80 = oversold, above -20 = overbought",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 14, "min": 2, "max": 100, "step": 1}],
                        "outputs": [{"name": "value", "label": "%R"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "presets": [
                            {"label": "Oversold (< -80)", "op": "lt", "value": -80},
                            {"label": "Overbought (> -20)", "op": "gt", "value": -20},
                        ],
                    },
                },
            },
            "cci": {
                "id": "cci",
                "label": "CCI",
                "description": "Commodity Channel Index — cyclical overbought/oversold",
                "indicators": {
                    "cci": {
                        "id": "cci",
                        "label": "CCI",
                        "description": "CCI measures deviation from typical price. Above +100 = overbought, below -100 = oversold",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 100, "step": 1}],
                        "outputs": [{"name": "value", "label": "CCI"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "presets": [
                            {"label": "Oversold (< -100)", "op": "lt", "value": -100},
                            {"label": "Overbought (> +100)", "op": "gt", "value": 100},
                            {"label": "Extreme oversold (< -200)", "op": "lt", "value": -200},
                            {"label": "Extreme overbought (> +200)", "op": "gt", "value": 200},
                        ],
                    },
                },
            },
            "mfi": {
                "id": "mfi",
                "label": "MFI",
                "description": "Money Flow Index — volume-weighted RSI",
                "indicators": {
                    "mfi": {
                        "id": "mfi",
                        "label": "MFI",
                        "description": "Money Flow Index — RSI weighted by volume. Above 80 = overbought, below 20 = oversold",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 14, "min": 2, "max": 100, "step": 1}],
                        "outputs": [{"name": "value", "label": "MFI"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "presets": [
                            {"label": "Oversold (< 20)", "op": "lt", "value": 20},
                            {"label": "Overbought (> 80)", "op": "gt", "value": 80},
                        ],
                    },
                },
            },
            "momentum": {
                "id": "momentum",
                "label": "Momentum",
                "description": "Rate of change and raw momentum",
                "indicators": {
                    "mom": {
                        "id": "mom",
                        "label": "Momentum",
                        "description": "Raw price momentum: close - close[N] periods ago",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 10, "min": 1, "max": 100, "step": 1}],
                        "outputs": [{"name": "value", "label": "Momentum"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                    },
                    "roc": {
                        "id": "roc",
                        "label": "ROC",
                        "description": "Rate of Change — % change over N periods",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 10, "min": 1, "max": 100, "step": 1}],
                        "outputs": [{"name": "value", "label": "ROC %"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                    },
                },
            },
        },
    },
    "volatility_indicators": {
        "id": "volatility_indicators",
        "label": "Volatility Indicators",
        "description": "Market volatility and standard deviation-based indicators",
        "icon": "🌊",
        "subcategories": {
            "bollinger_bands": {
                "id": "bollinger_bands",
                "label": "Bollinger Bands",
                "description": "Volatility bands around SMA — squeeze, breakouts, and reversals",
                "indicators": {
                    "bbands_upper": {
                        "id": "bbands_upper",
                        "label": "BB Upper",
                        "description": "Upper Bollinger Band — SMA + K * standard deviation",
                        "params": [
                            {"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 100, "step": 1},
                            {"name": "std_dev", "label": "Std dev", "type": "float", "default": 2.0, "min": 0.5, "max": 5.0, "step": 0.5},
                        ],
                        "outputs": [{"name": "value", "label": "Upper band"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below", "touch"],
                    },
                    "bbands_middle": {
                        "id": "bbands_middle",
                        "label": "BB Middle",
                        "description": "Middle Bollinger Band (SMA)",
                        "params": [
                            {"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 100, "step": 1},
                            {"name": "std_dev", "label": "Std dev", "type": "float", "default": 2.0, "min": 0.5, "max": 5.0, "step": 0.5},
                        ],
                        "outputs": [{"name": "value", "label": "Middle band"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below"],
                    },
                    "bbands_lower": {
                        "id": "bbands_lower",
                        "label": "BB Lower",
                        "description": "Lower Bollinger Band — SMA - K * standard deviation",
                        "params": [
                            {"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 100, "step": 1},
                            {"name": "std_dev", "label": "Std dev", "type": "float", "default": 2.0, "min": 0.5, "max": 5.0, "step": 0.5},
                        ],
                        "outputs": [{"name": "value", "label": "Lower band"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below", "touch"],
                    },
                    "bbands_width": {
                        "id": "bbands_width",
                        "label": "BB Width",
                        "description": "Bollinger Bandwidth — (upper - lower) / middle, squeeze indicator",
                        "params": [
                            {"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 100, "step": 1},
                            {"name": "std_dev", "label": "Std dev", "type": "float", "default": 2.0, "min": 0.5, "max": 5.0, "step": 0.5},
                        ],
                        "outputs": [{"name": "value", "label": "Bandwidth"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                    },
                    "bbands_percent_b": {
                        "id": "bbands_percent_b",
                        "label": "%B",
                        "description": "%B — where price sits within the bands (0 = lower, 1 = upper)",
                        "params": [
                            {"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 100, "step": 1},
                            {"name": "std_dev", "label": "Std dev", "type": "float", "default": 2.0, "min": 0.5, "max": 5.0, "step": 0.5},
                        ],
                        "outputs": [{"name": "value", "label": "%B"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "presets": [
                            {"label": "At lower band (%B < 0)", "op": "lt", "value": 0},
                            {"label": "At upper band (%B > 1)", "op": "gt", "value": 1},
                            {"label": "Below middle (%B < 0.5)", "op": "lt", "value": 0.5},
                        ],
                    },
                },
            },
            "atr": {
                "id": "atr",
                "label": "ATR",
                "description": "Average True Range — market volatility in price units",
                "indicators": {
                    "atr": {
                        "id": "atr",
                        "label": "ATR",
                        "description": "Average True Range — mean of true range over N periods",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 14, "min": 2, "max": 100, "step": 1}],
                        "outputs": [{"name": "value", "label": "ATR"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                    },
                    "atr_percent": {
                        "id": "atr_percent",
                        "label": "ATR%",
                        "description": "ATR as % of close — normalized volatility",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 14, "min": 2, "max": 100, "step": 1}],
                        "outputs": [{"name": "value", "label": "ATR%"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                    },
                },
            },
            "keltner_channels": {
                "id": "keltner_channels",
                "label": "Keltner Channels",
                "description": "Volatility-based channels using ATR",
                "indicators": {
                    "kc_upper": {
                        "id": "kc_upper",
                        "label": "KC Upper",
                        "description": "Upper Keltner Channel — EMA + multiplier * ATR",
                        "params": [
                            {"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 100, "step": 1},
                            {"name": "multiplier", "label": "ATR multiplier", "type": "float", "default": 2.0, "min": 0.5, "max": 5.0, "step": 0.5},
                        ],
                        "outputs": [{"name": "value", "label": "Upper channel"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below"],
                    },
                    "kc_lower": {
                        "id": "kc_lower",
                        "label": "KC Lower",
                        "description": "Lower Keltner Channel — EMA - multiplier * ATR",
                        "params": [
                            {"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 100, "step": 1},
                            {"name": "multiplier", "label": "ATR multiplier", "type": "float", "default": 2.0, "min": 0.5, "max": 5.0, "step": 0.5},
                        ],
                        "outputs": [{"name": "value", "label": "Lower channel"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below"],
                    },
                },
            },
        },
    },
    "volume_indicators": {
        "id": "volume_indicators",
        "label": "Volume Indicators",
        "description": "Volume-based indicators for confirmation and divergence",
        "icon": "📉",
        "subcategories": {
            "vwap": {
                "id": "vwap",
                "label": "VWAP",
                "description": "Volume-Weighted Average Price — intraday fair value",
                "indicators": {
                    "vwap": {
                        "id": "vwap",
                        "label": "VWAP",
                        "description": "Volume-Weighted Average Price — cumulative typical price * volume / cumulative volume",
                        "params": [],
                        "outputs": [{"name": "value", "label": "VWAP"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below"],
                    },
                },
            },
            "obv": {
                "id": "obv",
                "label": "OBV",
                "description": "On-Balance Volume — cumulative volume with sign from close direction",
                "indicators": {
                    "obv": {
                        "id": "obv",
                        "label": "OBV",
                        "description": "On-Balance Volume — volume accumulation/distribution",
                        "params": [],
                        "outputs": [{"name": "value", "label": "OBV"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                    },
                    "obv_sma": {
                        "id": "obv_sma",
                        "label": "OBV SMA",
                        "description": "Simple moving average of OBV for trend confirmation",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}],
                        "outputs": [{"name": "value", "label": "OBV SMA"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["obv_above_sma", "obv_below_sma"],
                    },
                },
            },
            "volume_profile": {
                "id": "volume_profile",
                "label": "Volume Profile",
                "description": "Volume at price levels",
                "indicators": {
                    "volume_sma": {
                        "id": "volume_sma",
                        "label": "Volume SMA",
                        "description": "Average volume over N periods",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}],
                        "outputs": [{"name": "value", "label": "Avg volume"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                    },
                    "volume_ratio": {
                        "id": "volume_ratio",
                        "label": "Volume Ratio",
                        "description": "Current volume / average volume — spike detection",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}],
                        "outputs": [{"name": "value", "label": "Volume ratio"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                    },
                },
            },
            "accumulation_distribution": {
                "id": "accumulation_distribution",
                "label": "A/D Line",
                "description": "Accumulation/Distribution Line — volume-weighted flow",
                "indicators": {
                    "ad_line": {
                        "id": "ad_line",
                        "label": "A/D Line",
                        "description": "Accumulation/Distribution — money flow based on close position within range",
                        "params": [],
                        "outputs": [{"name": "value", "label": "A/D"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                    },
                },
            },
        },
    },
    "statistical_indicators": {
        "id": "statistical_indicators",
        "label": "Statistical Indicators",
        "description": "Statistical measures for correlation, dispersion, and pattern analysis",
        "icon": "📐",
        "subcategories": {
            "correlation": {
                "id": "correlation",
                "label": "Correlation",
                "description": "Correlation between price and time (trend strength) or between assets",
                "indicators": {
                    "linear_reg": {
                        "id": "linear_reg",
                        "label": "Linear Regression",
                        "description": "Linear regression line value — trend direction and slope",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}],
                        "outputs": [{"name": "value", "label": "Regression line"}, {"name": "slope", "label": "Slope"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "comparisons": ["price_above", "price_below", "slope_positive", "slope_negative"],
                    },
                    "correlation": {
                        "id": "correlation",
                        "label": "Correlation",
                        "description": "Pearson correlation between two series over N periods",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}],
                        "outputs": [{"name": "value", "label": "R value"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                    },
                },
            },
            "z_score": {
                "id": "z_score",
                "label": "Z-Score",
                "description": "Standard deviation from mean — outlier detection",
                "indicators": {
                    "zscore": {
                        "id": "zscore",
                        "label": "Z-Score",
                        "description": "Number of standard deviations from the rolling mean",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}],
                        "outputs": [{"name": "value", "label": "Z-Score"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                        "presets": [
                            {"label": "2σ above mean (> 2)", "op": "gt", "value": 2},
                            {"label": "2σ below mean (< -2)", "op": "lt", "value": -2},
                            {"label": "Above 1σ (> 1)", "op": "gt", "value": 1},
                            {"label": "Below -1σ (< -1)", "op": "lt", "value": -1},
                        ],
                    },
                },
            },
            "entropy": {
                "id": "entropy",
                "label": "Entropy / Complexity",
                "description": "Market complexity and randomness measures",
                "indicators": {
                    "hurst": {
                        "id": "hurst",
                        "label": "Hurst Exponent",
                        "description": "Hurst exponent — < 0.5 = mean-reverting, > 0.5 = trending, 0.5 = random walk",
                        "params": [{"name": "period", "label": "Period", "type": "int", "default": 50, "min": 10, "max": 200, "step": 5}],
                        "outputs": [{"name": "value", "label": "Hurst"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                    },
                    "sample_entropy": {
                        "id": "sample_entropy",
                        "label": "Sample Entropy",
                        "description": "Sample entropy — lower values = more predictable/patterned",
                        "params": [
                            {"name": "period", "label": "Period", "type": "int", "default": 20, "min": 5, "max": 100, "step": 5},
                            {"name": "r", "label": "Tolerance (r * std)", "type": "float", "default": 0.2, "min": 0.05, "max": 1.0, "step": 0.05},
                        ],
                        "outputs": [{"name": "value", "label": "Entropy"}],
                        "ops": ["gt", "gte", "lt", "lte"],
                    },
                },
            },
        },
    },
    "pattern_indicators": {
        "id": "pattern_indicators",
        "label": "Pattern Recognition",
        "description": "Candlestick and chart pattern detection",
        "icon": "🔍",
        "subcategories": {
            "candlestick_single": {
                "id": "candlestick_single",
                "label": "Single Candle Patterns",
                "description": "Single-candlestick reversal and continuation patterns",
                "indicators": {
                    "doji": {"id": "doji", "label": "Doji", "description": "Open ≈ close — indecision", "params": [{"name": "tolerance", "label": "Tolerance %", "type": "float", "default": 0.1, "min": 0.01, "max": 1.0, "step": 0.05}], "outputs": [{"name": "value", "label": "Doji flag"}], "ops": ["eq"]},
                    "hammer": {"id": "hammer", "label": "Hammer", "description": "Small body, long lower wick — bullish reversal", "params": [], "outputs": [{"name": "value", "label": "Hammer flag"}], "ops": ["eq"]},
                    "shooting_star": {"id": "shooting_star", "label": "Shooting Star", "description": "Small body, long upper wick — bearish reversal", "params": [], "outputs": [{"name": "value", "label": "Star flag"}], "ops": ["eq"]},
                    "marubozu": {"id": "marubozu", "label": "Marubozu", "description": "No wicks — strong momentum", "params": [], "outputs": [{"name": "value", "label": "Marubozu flag"}], "ops": ["eq"]},
                    "spinning_top": {"id": "spinning_top", "label": "Spinning Top", "description": "Small body, wicks on both sides — weakening momentum", "params": [], "outputs": [{"name": "value", "label": "Spinning top flag"}], "ops": ["eq"]},
                },
            },
            "candlestick_double": {
                "id": "candlestick_double",
                "label": "Two-Candle Patterns",
                "description": "Two-candlestick reversal and continuation patterns",
                "indicators": {
                    "engulfing": {"id": "engulfing", "label": "Engulfing", "description": "Second candle body fully engulfs first — strong reversal", "params": [], "outputs": [{"name": "value", "label": "Engulfing flag"}], "ops": ["eq"]},
                    "harami": {"id": "harami", "label": "Harami", "description": "Small candle inside previous large candle — reversal signal", "params": [], "outputs": [{"name": "value", "label": "Harami flag"}], "ops": ["eq"]},
                    "piercing": {"id": "piercing", "label": "Piercing Line", "description": "Bullish reversal — second candle closes above midpoint of first", "params": [], "outputs": [{"name": "value", "label": "Piercing flag"}], "ops": ["eq"]},
                    "dark_cloud": {"id": "dark_cloud", "label": "Dark Cloud Cover", "description": "Bearish reversal — second candle closes below midpoint of first", "params": [], "outputs": [{"name": "value", "label": "Dark cloud flag"}], "ops": ["eq"]},
                },
            },
            "candlestick_triple": {
                "id": "candlestick_triple",
                "label": "Three-Candle Patterns",
                "description": "Three-candlestick reversal and continuation patterns",
                "indicators": {
                    "morning_star": {"id": "morning_star", "label": "Morning Star", "description": "Bear candle → doji/hammer → bull candle — bullish reversal", "params": [], "outputs": [{"name": "value", "label": "Morning star flag"}], "ops": ["eq"]},
                    "evening_star": {"id": "evening_star", "label": "Evening Star", "description": "Bull candle → doji/star → bear candle — bearish reversal", "params": [], "outputs": [{"name": "value", "label": "Evening star flag"}], "ops": ["eq"]},
                    "three_white_soldiers": {"id": "three_white_soldiers", "label": "Three White Soldiers", "description": "Three consecutive bull candles — strong uptrend", "params": [], "outputs": [{"name": "value", "label": "Soldiers flag"}], "ops": ["eq"]},
                    "three_black_crows": {"id": "three_black_crows", "label": "Three Black Crows", "description": "Three consecutive bear candles — strong downtrend", "params": [], "outputs": [{"name": "value", "label": "Crows flag"}], "ops": ["eq"]},
                },
            },
            "chart_patterns": {
                "id": "chart_patterns",
                "label": "Chart Patterns",
                "description": "Multi-bar chart pattern detection",
                "indicators": {
                    "double_top": {"id": "double_top", "label": "Double Top", "description": "Two peaks at similar level — bearish reversal", "params": [{"name": "lookback", "label": "Lookback bars", "type": "int", "default": 20, "min": 5, "max": 100, "step": 5}], "outputs": [{"name": "value", "label": "Double top flag"}], "ops": ["eq"]},
                    "double_bottom": {"id": "double_bottom", "label": "Double Bottom", "description": "Two troughs at similar level — bullish reversal", "params": [{"name": "lookback", "label": "Lookback bars", "type": "int", "default": 20, "min": 5, "max": 100, "step": 5}], "outputs": [{"name": "value", "label": "Double bottom flag"}], "ops": ["eq"]},
                    "head_shoulders": {"id": "head_shoulders", "label": "Head & Shoulders", "description": "Three peaks: lower, higher, lower — bearish reversal", "params": [{"name": "lookback", "label": "Lookback bars", "type": "int", "default": 40, "min": 10, "max": 200, "step": 10}], "outputs": [{"name": "value", "label": "H&S flag"}], "ops": ["eq"]},
                },
            },
        },
    },
    "custom": {
        "id": "custom",
        "label": "Custom Indicators",
        "description": "AI-generated, research-catalog, and user-defined custom indicators and patterns",
        "icon": "🧩",
        "is_custom": True,
        "subcategories": {
            "custom_indicators": {
                "id": "custom_indicators",
                "label": "Custom",
                "description": "Custom indicators loaded from custom_types/ and AI-generated definitions",
                "indicators": {},
            },
            "custom_candles": {
                "id": "custom_candles",
                "label": "CDL Patterns (Custom)",
                "description": "Extended candlestick pattern library from TA-Lib catalog",
                "indicators": {},
            },
        },
    },
    "price_actions": {
        "id": "price_actions",
        "label": "Price Action",
        "description": "Raw price-based conditions without indicator computation",
        "icon": "💰",
        "subcategories": {
            "price_levels": {
                "id": "price_levels",
                "label": "Price Levels",
                "description": "Support/resistance and price range conditions",
                "indicators": {
                    "close": {"id": "close", "label": "Close price", "description": "Candle close price", "params": [], "outputs": [{"name": "value", "label": "Close"}], "ops": ["gt", "gte", "lt", "lte"]},
                    "open": {"id": "open", "label": "Open price", "description": "Candle open price", "params": [], "outputs": [{"name": "value", "label": "Open"}], "ops": ["gt", "gte", "lt", "lte"]},
                    "high": {"id": "high", "label": "High price", "description": "Candle high price", "params": [], "outputs": [{"name": "value", "label": "High"}], "ops": ["gt", "gte", "lt", "lte"]},
                    "low": {"id": "low", "label": "Low price", "description": "Candle low price", "params": [], "outputs": [{"name": "value", "label": "Low"}], "ops": ["gt", "gte", "lt", "lte"]},
                    "atr_stop": {"id": "atr_stop", "label": "ATR Stop", "description": "Price distance from N-period low/high as multiple of ATR", "params": [{"name": "period", "label": "Period", "type": "int", "default": 20, "min": 2, "max": 100, "step": 1}, {"name": "multiplier", "label": "ATR multiplier", "type": "float", "default": 3.0, "min": 0.5, "max": 10.0, "step": 0.5}], "outputs": [{"name": "value", "label": "ATR stop"}], "ops": ["gt", "gte", "lt", "lte"]},
                },
            },
            "range_breakouts": {
                "id": "range_breakouts",
                "label": "Range Breakouts",
                "description": "Breakout from consolidation ranges",
                "indicators": {
                    "range_high": {"id": "range_high", "label": "Range High", "description": "N-period highest high", "params": [{"name": "period", "label": "Lookback", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}], "outputs": [{"name": "value", "label": "Range high"}], "ops": ["gt", "gte", "lt", "lte"]},
                    "range_low": {"id": "range_low", "label": "Range Low", "description": "N-period lowest low", "params": [{"name": "period", "label": "Lookback", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}], "outputs": [{"name": "value", "label": "Range low"}], "ops": ["gt", "gte", "lt", "lte"]},
                    "breakout_high": {"id": "breakout_high", "label": "High Breakout", "description": "Close > N-period high — bullish breakout", "params": [{"name": "period", "label": "Lookback", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}], "outputs": [{"name": "value", "label": "Breakout flag"}], "ops": ["eq"]},
                    "breakout_low": {"id": "breakout_low", "label": "Low Breakout", "description": "Close < N-period low — bearish breakdown", "params": [{"name": "period", "label": "Lookback", "type": "int", "default": 20, "min": 2, "max": 200, "step": 1}], "outputs": [{"name": "value", "label": "Breakout flag"}], "ops": ["eq"]},
                },
            },
        },
    },
}


def flatten_registry():
    """Flatten the registry into a searchable list of condition entries.
    
    Each entry: { id, label, description, category, subcategory,
                  params, outputs, ops, presets, comparisons, unit,
                  default_op, default_value }
    """
    entries = []
    for cat_id, cat in CONDITION_REGISTRY.items():
        for sub_id, sub in cat.get("subcategories", {}).items():
            # Threshold metrics (from ohlcv_metrics threshold subcategory)
            if "metrics" in sub:
                for m_id, m in sub["metrics"].items():
                    entry = {
                        "id": m_id,
                        "label": m["label"],
                        "description": m["description"],
                        "category": cat_id,
                        "category_label": cat["label"],
                        "subcategory": sub_id,
                        "subcategory_label": sub["label"],
                        "type": "metric",
                        "params": [],
                        "outputs": [{"name": m_id, "label": m["label"]}],
                        "ops": m.get("ops", ["gt", "gte", "lt", "lte"]),
                        "unit": m.get("unit", ""),
                        "default_op": m.get("default_op", "gt"),
                        "default_value": m.get("default_value", 0),
                        "presets": m.get("presets", []),
                        "comparisons": m.get("comparisons", []),
                    }
                    entries.append(entry)
                # Auto-generate pctl variants for ohlcv_metrics
                if cat_id == "ohlcv_metrics" and sub_id == "threshold":
                    pctl_sub = cat["subcategories"].get("pctl", {})
                    for m_id, m in sub["metrics"].items():
                        pctl_entry = {
                            "id": "pctl_" + m_id,
                            "label": "Pctl(" + m["label"] + ")",
                            "description": "Percentile rank of " + m["description"],
                            "category": cat_id,
                            "category_label": cat["label"],
                            "subcategory": "pctl",
                            "subcategory_label": "Percentile",
                            "type": "percentile",
                            "params": [],
                            "outputs": [{"name": "pctl_" + m_id, "label": "Pctl(" + m["label"] + ")"}],
                            "ops": pctl_sub.get("ops", ["gte", "gt", "lte", "lt"]),
                            "unit": "%",
                            "default_op": pctl_sub.get("default_op", "gte"),
                            "default_value": pctl_sub.get("default_value", 80),
                            "presets": [
                                {"label": "Top 10%", "op": "gte", "value": 90},
                                {"label": "Top 20%", "op": "gte", "value": 80},
                                {"label": "Bottom 10%", "op": "lte", "value": 10},
                                {"label": "Bottom 20%", "op": "lte", "value": 20},
                            ],
                            "comparisons": [],
                        }
                        entries.append(pctl_entry)
            # Indicators (from all other subcategories)
            if "indicators" in sub:
                for ind_id, ind in sub["indicators"].items():
                    entry = {
                        "id": ind_id,
                        "label": ind["label"],
                        "description": ind["description"],
                        "category": cat_id,
                        "category_label": cat["label"],
                        "subcategory": sub_id,
                        "subcategory_label": sub["label"],
                        "type": "indicator",
                        "params": ind.get("params", []),
                        "outputs": ind.get("outputs", []),
                        "ops": ind.get("ops", ["gt", "gte", "lt", "lte"]),
                        "unit": "",
                        "default_op": ind.get("default_op", "gt"),
                        "default_value": ind.get("default_value", 0),
                        "presets": ind.get("presets", []),
                        "comparisons": ind.get("comparisons", []),
                    }
                    entries.append(entry)
    return entries


FLAT_REGISTRY = flatten_registry()

# Extend with custom types (catalog + AI-generated)
for _ce in _CUSTOM_ENTRIES:
    # Avoid duplicate ids
    if not any(e["id"] == _ce["id"] for e in FLAT_REGISTRY):
        _ce["is_custom"] = True
        FLAT_REGISTRY.append(_ce)

# Populate CONDITION_REGISTRY custom subcategories so the browser shows them
if _CUSTOM_ENTRIES:
    custom_cat = CONDITION_REGISTRY.get("custom", {})
    custom_inds_sub = custom_cat.get("subcategories", {}).get("custom_indicators", {})
    custom_cdl_sub = custom_cat.get("subcategories", {}).get("custom_candles", {})
    if custom_inds_sub is not None:
        for _ce in _CUSTOM_ENTRIES:
            ce_cat = _ce.get("category_label", "").lower()
            if "cdl" in ce_cat or "candle" in ce_cat or "pattern" in ce_cat:
                if custom_cdl_sub is not None:
                    custom_cdl_sub.setdefault("indicators", {})[_ce["id"]] = {
                        "id": _ce["id"],
                        "label": _ce.get("label", _ce["id"]),
                        "description": _ce.get("description", ""),
                        "is_custom": True,
                        "params": _ce.get("params", []),
                        "outputs": _ce.get("outputs", []),
                        "ops": _ce.get("ops", ["gt", "gte", "lt", "lte"]),
                    }
            else:
                if custom_inds_sub is not None:
                    custom_inds_sub.setdefault("indicators", {})[_ce["id"]] = {
                        "id": _ce["id"],
                        "label": _ce.get("label", _ce["id"]),
                        "description": _ce.get("description", ""),
                        "is_custom": True,
                        "params": _ce.get("params", []),
                        "outputs": _ce.get("outputs", []),
                        "ops": _ce.get("ops", ["gt", "gte", "lt", "lte"]),
                    }


def search_conditions(query: str, max_results: int = 10) -> list[dict]:
    """Fuzzy-search the condition registry by id, label, description, or category."""
    query = query.lower().strip()
    if not query:
        return FLAT_REGISTRY[:max_results]

    scored = []
    for entry in FLAT_REGISTRY:
        score = 0
        # Exact id match
        if query == entry["id"].lower():
            score = 100
        # Prefix id match
        elif entry["id"].lower().startswith(query):
            score = 80
        # Exact label match
        elif query == entry["label"].lower():
            score = 75
        # Label contains query
        elif query in entry["label"].lower():
            score = 60
        # Description contains query
        elif query in entry["description"].lower():
            score = 40
        # Category or subcategory matches
        elif query in entry["category_label"].lower() or query in entry["subcategory_label"].lower():
            score = 30
        # Partial token match (e.g. "sma" matches "sma_crossover")
        elif any(query in part for part in entry["id"].lower().split("_")):
            score = 20
        # Param name match (e.g. "period" matches anything with a period param)
        elif any(query in p.get("label", p.get("name", "")).lower() for p in entry.get("params", [])):
            score = 10

        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: -x[0])
    results = [s[1] for s in scored[:max_results]]

    # Also search custom condition templates if few results
    if len(results) < max_results:
        custom_results = search_custom_conditions(query, max_results - len(results))
        # Add template refs
        for tmpl in custom_results:
            results.append({
                "id": "template:" + tmpl["id"],
                "label": "📋 " + tmpl.get("label", tmpl["id"]),
                "description": tmpl.get("description", ""),
                "category": "custom_templates",
                "category_label": "🧩 Custom Templates",
                "subcategory": "custom_templates",
                "subcategory_label": "AI Condition Templates",
                "type": "condition_template",
                "template": tmpl.get("template", {}),
                "params": [],
                "outputs": [],
                "ops": [],
                "is_custom": True,
                "origin": "condition_template",
            })

    return results
