read -p "Enter cluster name: " cluster_name
read -p "Enter to be generated password: " password

kubectl --context $cluster_name -n external-secrets delete secret secret-store-password
kubectl --context $cluster_name -n external-secrets create secret generic secret-store-password --from-literal=password=$password