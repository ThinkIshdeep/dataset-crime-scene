import io
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GroupShuffleSplit
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from .core import Base, decoded

class Engine(Base):
    actions = Base.actions | {'upload', 'audit', 'configure'}

    def __init__(self):
        super().__init__()
        self.reset({})

    def reset(self, p):
        r = np.random.default_rng(42)
        base = pd.DataFrame({'subject': np.arange(220), 'age': r.integers(18, 75, 220), 'signal': r.normal(size=220), 'outcome': r.integers(0, 2, 220)})
        base['post_event_result'] = base['outcome'] + 0.01 * r.normal(size=220)
        df = pd.concat([base] * 3, ignore_index=True)
        df['day'] = np.tile(np.arange(220), 3)
        self.state = {'name': 'synthetic-leaky-cohort.csv', 'records': df.to_dict('records'), 'target': 'outcome', 'group': 'subject', 'time': 'day', 'unavailable': ['post_event_result'], 'findings': [], 'last_result': None}
        self.audit({})

    def upload(self, p):
        text = decoded(p).decode('utf-8-sig') if 'data' in p else str(p.get('text', ''))
        df = self.csv_records(text)
        if not 20 <= len(df) <= 50000 or len(df.columns) > 100:
            raise ValueError('Use 20–50,000 rows and at most 100 columns')
        self.state.update(name=str(p.get('name', 'uploaded.csv')), records=df.replace({np.nan: None}).to_dict('records'), target=str(p.get('target', df.columns[-1])), group='', time='', unavailable=[], findings=[], last_result=None)
        return self.audit({})

    def configure(self, p):
        df = pd.DataFrame(self.state['records'])
        for k in ['target', 'group', 'time']:
            if k in p:
                value = str(p[k])
                if value and value not in df.columns:
                    raise ValueError(f'Unknown column: {value}')
                self.state[k] = value
        if 'unavailable' in p:
            cols = p['unavailable'] if isinstance(p['unavailable'], list) else [x.strip() for x in str(p['unavailable']).split(',') if x.strip()]
            if any((c not in df for c in cols)):
                raise ValueError('Unknown unavailable feature')
            self.state['unavailable'] = cols
        return self.audit({})

    def audit(self, p):
        s = self.state
        df = pd.DataFrame(s['records'])
        target = s['target']
        if target not in df:
            raise ValueError('Target column not found')
        findings = []
        dup = int(df.duplicated().sum())
        if dup:
            findings.append({'type': 'duplicates', 'severity': 'confirmed', 'count': dup, 'evidence': f'{dup} exact duplicate records. Keep duplicate groups together or deduplicate before splitting.'})
        for col in s['unavailable']:
            findings.append({'type': 'prediction_time_unavailable', 'severity': 'confirmed by supplied metadata', 'column': col, 'evidence': 'User/task metadata marks this feature unavailable at prediction time.'})
        numeric = df.select_dtypes('number')
        if target in numeric:
            corr = numeric.corr()[target].drop(target)
            for c, v in corr.items():
                if abs(v) > 0.93:
                    findings.append({'type': 'target_proxy', 'severity': 'review', 'column': c, 'correlation': float(v), 'evidence': 'High correlation alone does not establish leakage. Check availability and provenance.'})
        if s['group'] and s['group'] in df:
            a, b = train_test_split(np.arange(len(df)), random_state=42, test_size=0.25)
            overlap = set(df.iloc[a][s['group']]) & set(df.iloc[b][s['group']])
            if overlap:
                findings.append({'type': 'entity_overlap', 'severity': 'confirmed overlap; task dependent', 'count': len(overlap), 'evidence': 'Random record split shares entities. A new-entity task requires a grouped split.'})
        for c in df.columns:
            missing = float(df[c].isna().mean())
            if missing > 0.2:
                findings.append({'type': 'missingness', 'severity': 'review', 'column': c, 'fraction': missing, 'evidence': 'More than 20% missing values.'})
        s['findings'] = findings
        s['profile'] = {'rows': len(df), 'columns': [{'name': c, 'dtype': str(df[c].dtype), 'missing': int(df[c].isna().sum()), 'unique': int(df[c].nunique())} for c in df], 'duplicate_rows': dup}
        return {'findings': findings, 'profile': s['profile']}

    def fit(self, df, target, features, train, test):
        if not features:
            raise ValueError('No features remain after correction')
        X = df[features].copy()
        numeric = X.select_dtypes('number').columns.tolist()
        categorical = [c for c in features if c not in numeric]
        for c in categorical:
            X[c] = X[c].fillna('(missing)').astype(str)
        transform = ColumnTransformer([('numeric', make_pipeline(SimpleImputer(strategy='median', keep_empty_features=True)), numeric), ('categorical', OneHotEncoder(handle_unknown='ignore'), categorical)])
        m = make_pipeline(transform, RandomForestClassifier(n_estimators=80, max_depth=12, random_state=42, n_jobs=1))
        m.fit(X.iloc[train], df[target].iloc[train].astype(str))
        pred = m.predict(X.iloc[test])
        y = df[target].iloc[test].astype(str)
        return {'accuracy': float(accuracy_score(y, pred)), 'macro_f1': float(f1_score(y, pred, average='macro')), 'train_rows': len(train), 'test_rows': len(test), 'features': features}

    def evaluate(self, p):
        s = self.state
        df = pd.DataFrame(s['records']).dropna(subset=[s['target']]).reset_index(drop=True)
        target = s['target']
        if not 2 <= df[target].nunique() <= 20:
            raise ValueError('This release evaluates classification targets with 2–20 classes')
        ids = np.arange(len(df))
        a, b = train_test_split(ids, test_size=0.25, random_state=42)
        features = [c for c in df if c != target]
        before = self.fit(df, target, features, a, b)
        self.check_cancel()
        if s['group'] and df[s['group']].nunique() > 2:
            a, b = next(GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42).split(df, groups=df[s['group']]))
            strategy = 'grouped new-entity holdout'
        elif s['time']:
            order = np.argsort(df[s['time']].values)
            a, b = (order[:int(0.75 * len(df))], order[int(0.75 * len(df)):])
            strategy = 'chronological holdout'
        else:
            df = df.drop_duplicates().reset_index(drop=True)
            a, b = train_test_split(np.arange(len(df)), test_size=0.25, random_state=42)
            strategy = 'deduplicated random holdout'
        safe = [c for c in features if c not in s['unavailable'] and c not in [s['group'], s['time']]]
        after = self.fit(df, target, safe, a, b)
        out = {'original': before, 'corrected': after, 'strategy': strategy, 'excluded': s['unavailable'], 'note': 'Different split protocols answer different generalization questions. Only explicitly unavailable features are excluded as leaks; correlations remain review findings.'}
        s['last_result'] = out
        return out
