from market.universe import UniverseManager

manager = UniverseManager()

df = manager.load_master_universe()

print(df)