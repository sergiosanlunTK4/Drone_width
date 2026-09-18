import numpy as np
import pandas as pd

def generate_lhs_doe(n_samples=100, random_seed=42):
    np.random.seed(random_seed)
    dims = 4
    result = np.empty((n_samples, dims))
    for i in range(dims):
        perm = np.random.permutation(n_samples)
        result[:, i] = (perm + np.random.uniform(size=n_samples)) / n_samples
        
    l_bounds = np.array([2.0, 1.5, 150.0, 0.1])
    u_bounds = np.array([10.0, 6.0, 400.0, 1.0])
    scaled = result * (u_bounds - l_bounds) + l_bounds
    
    doe_df = pd.DataFrame(scaled, columns=['V_inf_ms', 'Height_m', 'DV0.5_um', 'Payload_Fraction'])
    doe_df['Atomizers'] = np.random.choice([2, 4], size=n_samples)
    doe_df['Platform'] = np.random.choice(['T25P', 'T55', 'T70P', 'T100'], size=n_samples)
    return doe_df

if __name__ == '__main__':
    doe = generate_lhs_doe(100)
    doe.to_csv('data/processed/doe_master_plan.csv', index=False)
    print(f"Generated master DOE plan with {len(doe)} runs successfully.")
    print(doe.head(10))
