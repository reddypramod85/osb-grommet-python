#Show cluster is up and running with nodes
kubectl cluster-info
kubectl get nodes -o wide

#Get all pods across all namespaces:
kubectl get pods --all-namespaces

#Show cluster service broker:
cat grommet-broker-clusterservicebroker.yaml

#First we need to connect our Kubernetes API server to the developed catalog. Therefore we need to define a ClusterServiceBroker:

Create a name space for grommet broker:
export NS="grommet-ns"
kubectl create ns $NS

# Creating Cluster service broker:
kubectl apply -f grommet-broker-clusterservicebroker.yaml

#List broker
kubectl get clusterservicebroker

#Describe Broker
kubectl describe ClusterServiceBroker grommet-broker -n $NS

#Show the catalog is fetched

#List services/Classes:
kubectl get clusterserviceclasses

#List Plans
kubectl get clusterserviceplans

Clear

Ls

#Show grommet-broker-instance file

Cat grommet-broker-instance.yaml

#Create Service Instance:
kubectl create -f grommet-broker-instance.yaml

#Describe Service Instance:
kubectl get serviceinstances -n grommet-ns grommet-broker-instance -o yaml

#Check Secrets:
kubectl get secrets -n grommet-ns

cat grommet-broker-binding.yaml

#Create Binding:
kubectl create -f grommet-broker-binding.yaml


#Describe binding:
kubectl get servicebindings -n grommet-ns grommet-broker-binding -o yaml

#Check Secrets:
kubectl get secrets -n grommet-ns
#Describe Secrets:
kubectl describe secrets/grommet-broker-binding -n grommet-ns
#View Secret file contents:
kubectl get secret grommet-broker-binding -n grommet-ns -o yaml
#Decode:
echo 'aHR0cDovLzM0LjIwNy4yMDAuMTc3OjMwMDA=' | base64 --decode

#Browser:
Open the url and show the application is running

#Deleting the service binding:
svcat unbind -n grommet-ns grommet-broker-instance

#Check Secrets:
You should see the secrets get deleted
kubectl get secrets -n grommet-ns

#Deprovision the Service Instance:
svcat deprovision -n grommet-ns grommet-broker-instance

#Deleting the Cluster Service Broker:
kubectl delete clusterservicebrokers grommet-broker

#List broker
kubectl get clusterservicebroker
