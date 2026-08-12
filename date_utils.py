from datetime import date


def get_date_context():

    today = date.today()

    current_year = today.year
    previous_year = current_year - 1

    current_month = today.month

    if current_month == 1:
        previous_month = 12
        previous_month_year = current_year - 1
    else:
        previous_month = current_month - 1
        previous_month_year = current_year

    return {
        "today": str(today),

        "current_year": current_year,
        "previous_year": previous_year,

        "previous_year_start": f"{previous_year}-01-01",
        "current_year_start": f"{current_year}-01-01",

        "previous_month": previous_month,
        "previous_month_year": previous_month_year,
    }
def get_date_condition(time_period):

    context = get_date_context()

    if time_period == "last year":

        return (
            f"order_date >= '{context['previous_year_start']}' "
            f"AND order_date < '{context['current_year_start']}'"
        )

    if time_period == "this year":

        return (
            f"order_date >= '{context['current_year_start']}' "
            f"AND order_date <= '{context['today']}'"
        )

    if time_period == "last month":

        year = context["previous_month_year"]
        month = context["previous_month"]

        if month == 12:
            next_year = year + 1
            next_month = 1
        else:
            next_year = year
            next_month = month + 1

        start_date = f"{year}-{month:02d}-01"
        end_date = f"{next_year}-{next_month:02d}-01"

        return (
            f"order_date >= '{start_date}' "
            f"AND order_date < '{end_date}'"
        )

    return None