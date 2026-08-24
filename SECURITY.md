# Politique de sécurité

Ne publiez pas de vulnérabilité ni de jeu de données sensible dans une issue publique. Utilisez le canal privé de signalement de sécurité du dépôt GitHub.

L'application traite les CSV dans la mémoire du processus Streamlit. Un déploiement de production doit ajouter authentification, chiffrement en transit, limitation des journaux, contrôle des accès, politique de rétention et isolation des sessions. Le projet n'envoie pas de données à une API externe.

Les versions de dépendances sont bornées dans `pyproject.toml`. Les correctifs de sécurité doivent être évalués et publiés rapidement.

