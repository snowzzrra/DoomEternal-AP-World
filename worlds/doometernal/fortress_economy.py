"""Battery limits shared by campaign generation and room validation."""


def battery_surplus_limit(cost, percent):
    return (cost * percent + 99) // 100
