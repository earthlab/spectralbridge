"""One color contract: category hues, model hues, and distinct quantitative scales."""

CATEGORIES = (
    "Deciduous",
    "Evergreen",
    "Herbaceous",
    "Non-vegetated & dead",
    "Woody shrub",
)
PALETTE = {
    "text": "#252A31",
    "muted": "#707780",
    "light": "#D8DDE3",
    "gap": "#ECEDEF",
    "selected": "#6495ED",
    "random": "#9EA5AD",
    "effect_negative": "#C18B70",
    "effect_zero": "#FAFAF8",
    "effect_positive": "#5278B5",
    "confusion_low": "#F7F9FC",
    "confusion_high": "#547CB9",
    "categories": dict(
        zip(CATEGORIES, ["#48745A", "#233F35", "#8C7228", "#896A59", "#815681"])
    ),
    "models": {
        "Training prior": "#B3B8BE",
        "MESMA15": "#AD775A",
        "Ridge15": "#747E89",
        "Ridge120": "#252A31",
    },
    "model_styles": {"MESMA15": (0, (3, 2)), "Ridge120": "-"},
    "domain_markers": {"plant": "o", "site": "s"},
    "domain_lines": {"plant": "-", "site": (0, (4, 2))},
}
