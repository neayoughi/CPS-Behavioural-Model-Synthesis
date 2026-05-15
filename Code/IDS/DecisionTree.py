
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV, KFold
from sklearn.tree import DecisionTreeClassifier, plot_tree, export_text
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder
from imblearn.over_sampling import SMOTE


def load_and_preprocess_data(file_path):
    data = pd.read_csv(file_path)
    features = ['Unreplied'] #'Flow', 'Unreplied'
    X = data[features]
    y = data['State']
    return X, y

def find_best_ccp_alpha(X, y):
    parameters = {'ccp_alpha': [0.001, 0.01, 0.1, 1, 10]}
    clf = DecisionTreeClassifier(random_state=42)
    clf_cv = GridSearchCV(clf, parameters, cv=5)
    clf_cv.fit(X, y)
    best_ccp_alpha = clf_cv.best_params_['ccp_alpha']
    return best_ccp_alpha

def split_data(X, y):
    return train_test_split(X, y, test_size=0.3, random_state=42)

def apply_smote(X_train, y_train):
    smote = SMOTE(random_state=42, k_neighbors=1)
    X_train_smote, y_train_smote = smote.fit_resample(X_train, y_train)
    return X_train_smote, y_train_smote


def train_decision_tree(X_train, y_train, ccp_alpha):
    # Added parameters to control overfitting
    # clf = DecisionTreeClassifier(random_state=42, ccp_alpha=ccp_alpha, max_depth=3, min_samples_leaf=5)
    clf = DecisionTreeClassifier(max_depth=3)
    clf.fit(X_train, y_train)
    return clf

def evaluate_model(clf, X_test, y_test):
    predictions = clf.predict(X_test)
    print(classification_report(y_test, predictions, zero_division=1))
    print(confusion_matrix(y_test, predictions))

def visualize_tree(clf, feature_names):
    plt.figure(figsize=(20, 10))
    plot_tree(clf, filled=True, feature_names=feature_names)
    plt.show()

def print_tree_text(clf, feature_names):
    tree_text = export_text(clf, feature_names=feature_names)
    print(tree_text)



# Main
if __name__ == "__main__":
    file_path = 'TimeSeriesData_DDoS.csv'
    X, y = load_and_preprocess_data(file_path)
    best_ccp_alpha = find_best_ccp_alpha(X, y)
    X_train, X_test, y_train, y_test = split_data(X, y)
    X_train_smote, y_train_smote = apply_smote(X_train, y_train)
    clf = train_decision_tree(X_train_smote, y_train_smote, best_ccp_alpha)
    evaluate_model(clf, X_test, y_test)
    feature_names = list(X.columns)
    visualize_tree(clf, feature_names)
    print_tree_text(clf, feature_names)



