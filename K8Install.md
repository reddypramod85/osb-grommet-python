# Create Demo Setup
This document talks about how to create the OSB demo setup including network, docker, Kubernetes, K8 service catalog and registering grommet OSB broker.

## Network
There are three CentOS7 VM's in this demo as shown below.

| Node    | Hostname   | Private IP  | K8s    |
| :-----: |:------------:|:-----------:| :-----:|
| Centos7-master    | k8master.etss.lab    |  192.168.171.102 | Master |
| Centos7-worker   | k8worker1.etss.lab   |  192.168.171.107 | Worker1 |
| Centos7-worker  | k8worker2.etss.lab   |  192.168.171.103 | Worker2 |

#### Reference
Install kubeadm https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/

Create-cluster-kubeadm https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/

Cluster administration addons https://kubernetes.io/docs/concepts/cluster-administration/addons/

Service Catalog https://kubernetes.io/docs/concepts/extend-kubernetes/service-catalog/

Install service catalog using helm https://kubernetes.io/docs/tasks/service-catalog/install-service-catalog-using-helm/

Installing the service catalog cli https://svc-cat.io/docs/install/#installing-the-service-catalog-cli


## Virtual Machines
We configure the k8master.etss.lab as K8s master node and k8worker1.etss.lab and k8worker2.etss.lab as K8s worker nodes and install different components of K8s on them.
### System
First, we configure the hostnames of the three VM's which are used as K8s node name.
Modify ```/etc/hostname``` as:
```bash
127.0.0.1       localhost
192.168.171.102     k8master.etss.lab
192.168.171.107     k8worker1.etss.lab
192.168.171.103     k8worker2.etss.lab
```
And run ```sudo hostnamectl set-hostname k8-X-.etss.lab``` on each machine.

### Proxy (optional)
If the machines are running inside HPE network, we need to configure proxy.
Add the following to ```/etc/environment```:
```bash
http_proxy=http://proxy.houston.hpecorp.net:8088
HTTP_PROXY=http://proxy.houston.hpecorp.net:8088
https_proxy=http://proxy.houston.hpecorp.net:8088
HTTPS_PROXY=http://proxy.houston.hpecorp.net:8088
no_proxy=localhost,127.0.0.1,192.168.171.0/24,10.96.0.0/16,10.244.0.0/16,svc,.cluster.local,.etss.lab
NO_PROXY=localhost,127.0.0.1,192.168.171.0/24,10.96.0.0/16,10.244.0.0/16,svc,.cluster.local,.etss.lab
```
In case different tools may pickup proxy information from different configuration files, we also need to add the following to ```~/.bashrc``` and ```/root/.bashrc/```:
```
export http_proxy=http://proxy.houston.hpecorp.net:8088
export HTTP_PROXY=http://proxy.houston.hpecorp.net:8088
export https_proxy=http://proxy.houston.hpecorp.net:8088
export HTTPS_PROXY=http://proxy.houston.hpecorp.net:8088
export no_proxy=localhost,127.0.0.1,192.168.171.0/24,10.96.0.0/16,10.244.0.0/16,svc,.cluster.local,.etss.lab
export NO_PROXY=localhost,127.0.0.1,192.168.171.0/24,10.96.0.0/16,10.244.0.0/16,svc,.cluster.local,.etss.lab

```
* Note that ```no_proxy``` has to be set properly and exclude K8s related networks from proxy. Otherwise, you may experience various network problem for K8s. ```10.96.0.0/16``` is the default service network of K8s and ```10.244.0.0/16``` is the pod network for ```Flannel``` container network interface (CNI).

### Docker
We use Docker as the container runtime for K8s.
By default Docker uses ```cgroupfs``` as the cgroup driver. [However, this may cause problems for K8s](https://kubernetes.io/docs/setup/production-environment/container-runtimes/). Run the following commands to install Docker and configure cgroup driver as ```systemd```.
```bash
# Install Docker CE
## Set up the repository
### Install required packages.
yum install yum-utils device-mapper-persistent-data lvm2
### Add Docker repository.
yum-config-manager \
  --add-repo \
  https://download.docker.com/linux/centos/docker-ce.repo
## Install Docker CE.
yum update && yum install docker-ce-18.06.2.ce
## Create /etc/docker directory.
mkdir /etc/docker
# Setup daemon.
echo -e '{
"exec-opts": ["native.cgroupdriver=systemd"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  },
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ]
}' | sudo tee /etc/docker/daemon.json

mkdir -p /etc/systemd/system/docker.service.d
# add current user to docker user group
sudo usermod -aG docker ${USER} 
sudo systemctl enable docker
# Restart Docker
sudo systemctl daemon-reload
sudo systemctl restart docker.service
```
To verify, run the following:
```bash
$ docker info | grep Driver
Storage Driver: overlay2
Logging Driver: json-file
Cgroup Driver: systemd
#Test docker installation
$ docker run hello-world
```
#### Docker Proxy
You may also need to setup proxy if running inside HPE network. Add the following to ```/etc/systemd/system/docker.service.d/http-proxy.conf``` and restart docker ```sudo systemctl daemon-reload && sudo systemctl restart docker```:
```bash
[Service]
Environment="HTTP_PROXY=http://proxy.houston.hpecorp.net:8088/" "HTTPS_PROXY=http://proxy.houston.hpecorp.net:8088/"  "NO_PROXY=localhost,127.0.0.1,192.168.171.0/24,10.96.0.0/16,10.240.10.0/16"
```

### Kubernetes
[Since K8s doesn't work well with swap, we need to turn off swap.](https://github.com/kubernetes/kubernetes/issues/53533) Run ```sudo swapoff -a``` and add it to ```/etc/rc.local``` to disable swap after reboot. To verify swap is disabled:
```bash
$ free -h
              total        used        free      shared  buff/cache   available
Mem:            15G        161M         14G        9.1M        535M         15G
Swap:            0B          0B          0B
```

Then run the following commands to install ```kubeadm```, ```kubectl``` and ```kubelet```.
```bash
cat <<EOF > /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
exclude=kube*
EOF
# Set SELinux in permissive mode (effectively disabling it)
setenforce 0
sed -i 's/^SELINUX=enforcing$/SELINUX=permissive/' /etc/selinux/config
yum install -y kubelet kubeadm kubectl --disableexcludes=kubernetes
systemctl enable --now kubelet
cat <<EOF >  /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
EOF
sysctl --system


```
Then we need to configure K8s master node and worker nodes separately.
#### Master node
Run the following command to initialize the master node and install ```Flannel``` CNI:
```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16 --service-cidr=10.96.0.0/16 | tee kubeadm_init.log
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
```
* NOTE Run below commands if you get  ```[ERROR DirAvailable--var-lib-etcd]: /var/lib/etcd is not empty```
```bash
Cd /var/lib/etcd
Rm -rf member
```
The output of ```kubeadm init``` is stored in ```kubeadm_init.log``` and make sure there is no error or warning in the output. We will need to use the token and certificate in the output to add K8s worker nodes to this cluster. Here is an example of the output:
```bash
[root@k8master ~]# kubeadm init --pod-network-cidr=10.244.0.0/16 --service-cidr=10.96.0.0/16 | tee kubeadm_init.log
[init] Using Kubernetes version: v1.15.0
[preflight] Running pre-flight checks
[preflight] Pulling images required for setting up a Kubernetes cluster
[preflight] This might take a minute or two, depending on the speed of your internet connection
[preflight] You can also perform this action in beforehand using 'kubeadm config images pull'
[kubelet-start] Writing kubelet environment file with flags to file "/var/lib/kubelet/kubeadm-flags.env"
[kubelet-start] Writing kubelet configuration to file "/var/lib/kubelet/config.yaml"
[kubelet-start] Activating the kubelet service
[certs] Using certificateDir folder "/etc/kubernetes/pki"
[certs] Generating "etcd/ca" certificate and key
[certs] Generating "etcd/server" certificate and key
[certs] etcd/server serving cert is signed for DNS names [k8master.etss.lab localhost] and IPs [192.168.171.102 127.0.0.1 ::1]
[certs] Generating "etcd/peer" certificate and key
[certs] etcd/peer serving cert is signed for DNS names [k8master.etss.lab localhost] and IPs [192.168.171.102 127.0.0.1 ::1]
[certs] Generating "etcd/healthcheck-client" certificate and key
[certs] Generating "apiserver-etcd-client" certificate and key
[certs] Generating "ca" certificate and key
[certs] Generating "apiserver" certificate and key
[certs] apiserver serving cert is signed for DNS names [k8master.etss.lab kubernetes kubernetes.default kubernetes.default.svc kubernetes.default.svc.cluster.local] and IPs [10.96.0.1 192.168.171.102]
[certs] Generating "apiserver-kubelet-client" certificate and key
[certs] Generating "front-proxy-ca" certificate and key
[certs] Generating "front-proxy-client" certificate and key
[certs] Generating "sa" key and public key
[kubeconfig] Using kubeconfig folder "/etc/kubernetes"
[kubeconfig] Writing "admin.conf" kubeconfig file
[kubeconfig] Writing "kubelet.conf" kubeconfig file
[kubeconfig] Writing "controller-manager.conf" kubeconfig file
[kubeconfig] Writing "scheduler.conf" kubeconfig file
[control-plane] Using manifest folder "/etc/kubernetes/manifests"
[control-plane] Creating static Pod manifest for "kube-apiserver"
[control-plane] Creating static Pod manifest for "kube-controller-manager"
[control-plane] Creating static Pod manifest for "kube-scheduler"
[etcd] Creating static Pod manifest for local etcd in "/etc/kubernetes/manifests"
[wait-control-plane] Waiting for the kubelet to boot up the control plane as static Pods from directory "/etc/kubernetes/manifests". This can take up to 4m0s
[apiclient] All control plane components are healthy after 22.005808 seconds
[upload-config] Storing the configuration used in ConfigMap "kubeadm-config" in the "kube-system" Namespace
[kubelet] Creating a ConfigMap "kubelet-config-1.15" in namespace kube-system with the configuration for the kubelets in the cluster
[upload-certs] Skipping phase. Please see --upload-certs
[mark-control-plane] Marking the node k8master.etss.lab as control-plane by adding the label "node-role.kubernetes.io/master=''"
[mark-control-plane] Marking the node k8master.etss.lab as control-plane by adding the taints [node-role.kubernetes.io/master:NoSchedule]
[bootstrap-token] Using token: nm1u96.qunoq78mqp4migod
[bootstrap-token] Configuring bootstrap tokens, cluster-info ConfigMap, RBAC Roles
[bootstrap-token] configured RBAC rules to allow Node Bootstrap tokens to post CSRs in order for nodes to get long term certificate credentials
[bootstrap-token] configured RBAC rules to allow the csrapprover controller automatically approve CSRs from a Node Bootstrap Token
[bootstrap-token] configured RBAC rules to allow certificate rotation for all node client certificates in the cluster
[bootstrap-token] Creating the "cluster-info" ConfigMap in the "kube-public" namespace
[addons] Applied essential addon: CoreDNS
[addons] Applied essential addon: kube-proxy

Your Kubernetes control-plane has initialized successfully!

To start using your cluster, you need to run the following as a regular user:

  mkdir -p $HOME/.kube
  sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
  sudo chown $(id -u):$(id -g) $HOME/.kube/config

You should now deploy a pod network to the cluster.
Run "kubectl apply -f [podnetwork].yaml" with one of the options listed at:
  https://kubernetes.io/docs/concepts/cluster-administration/addons/

Then you can join any number of worker nodes by running the following on each as root:

kubeadm join 192.168.171.102:6443 --token nm1u96.qunoq78mqp4migod \
    --discovery-token-ca-cert-hash sha256:4407c1f30d58c138d2f36c1774bc1ded66a7c142484476d506eec4cd7827de84

```
* Note that here we use Flannel, but there are (others available)[https://kubernetes.io/docs/concepts/cluster-administration/networking/]. For ```Flannel``` to work correctly, you must pass ```--pod-network-cidr=10.244.0.0/16``` to ```kubeadm init```.
* By default, ```kubeadm init``` use ```10.96.0.0/12``` for ```--service-cidr```. It is better to set this in accordance with ```noproxy``` setting. Otherwise you may running into networking problems between services and pods.

Run the following command to make sure all pods are started successfully.
```bash
[root@k8master ~]# kubectl get pods --all-namespaces
NAMESPACE     NAME                                              READY   STATUS    RESTARTS   AGE
kube-system   coredns-5c98db65d4-r2vn2                          1/1     Running   0          3m38s
kube-system   coredns-5c98db65d4-rcwtg                          1/1     Running   0          3m38s
kube-system   etcd-k8master.etss.lab                      1/1     Running   0          2m50s
kube-system   kube-apiserver-k8master.etss.lab            1/1     Running   0          2m47s
kube-system   kube-controller-manager-k8master.etss.lab   1/1     Running   0          2m44s
kube-system   kube-flannel-ds-amd64-kzxth                       1/1     Running   0          100s
kube-system   kube-proxy-zkfkm                                  1/1     Running   0          3m38s
kube-system   kube-scheduler-k8master.etss.lab            1/1     Running   0          2m46s
```

### Worker node
Switch worker nodes and run the following to join the cluster:
```bash
kubeadm join 192.168.171.102:6443 --token nm1u96.qunoq78mqp4migod \
    --discovery-token-ca-cert-hash sha256:4407c1f30d58c138d2f36c1774bc1ded66a7c142484476d506eec4cd7827de84
```
Now, go back to master node and run the following to make sure all worker nodes are online.
```bash
[root@k8master ~]# kubectl get nodes -o wide
NAME                      STATUS   ROLES    AGE     VERSION   INTERNAL-IP       EXTERNAL-IP   OS-IMAGE                KERNEL-VERSION               CONTAINER-RUNTIME
k8master.etss.lab   Ready    master   5m42s   v1.15.0   192.168.171.102   <none>        CentOS Linux 7 (Core)   3.10.0-957.21.3.el7.x86_64   docker://18.6.2
k8worker1.etss.lab        Ready    <none>   12s     v1.15.0   192.168.171.107   <none>        CentOS Linux 7 (Core)   3.10.0-957.21.3.el7.x86_64   docker://18.6.2
k8worker2.etss.lab        Ready    <none>   12s     v1.15.0   192.168.171.103   <none>        CentOS Linux 7 (Core)   3.10.0-957.21.3.el7.x86_64   docker://18.6.2
```

#### Reference
- Installing Kubernetes with deployment tools, https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/
- How to Install and Configure Kubernetes and Docker on Ubuntu 18.04 LTS, https://www.howtoforge.com/tutorial/how-to-install-kubernetes-on-ubuntu/
- How To Install Kubernetes Cluster On Ubuntu 16.04, https://www.edureka.co/blog/install-kubernetes-on-ubuntu
- kubeadm 1.9.2 doesn't work over proxy, https://github.com/kubernetes/kubeadm/issues/687
- Installing a pod network add-on, https://kubernetes.io/docs/setup/independent/create-cluster-kubeadm/#pod-network

## Ghost Application
```bash
 kubectl run ghost --image=ghost --port=2368
 [root@k8master ~]# kubectl run ghost --image=ghost --port=2368
kubectl run --generator=deployment/apps.v1 is DEPRECATED and will be removed in a future version. Use kubectl run --generator=run-pod/v1 or kubectl create instead.
deployment.apps/ghost created
[root@k8master ~]# kubectl get deployment
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
ghost   0/1     1            0           12s
[root@k8master ~]# kubectl get pods
NAME                    READY   STATUS    RESTARTS   AGE
ghost-d685c98d8-8d6pf   1/1     Running   0          116s
[root@k8master ~]# kubectl describe deployment ghost
Name:                   ghost
Namespace:              default
CreationTimestamp:      Thu, 04 Jul 2019 08:11:29 +0200
Labels:                 run=ghost
Annotations:            deployment.kubernetes.io/revision: 1
Selector:               run=ghost
Replicas:               1 desired | 1 updated | 1 total | 1 available | 0 unavailable
StrategyType:           RollingUpdate
MinReadySeconds:        0
RollingUpdateStrategy:  25% max unavailable, 25% max surge
Pod Template:
  Labels:  run=ghost
  Containers:
   ghost:
    Image:        ghost
    Port:         2368/TCP
    Host Port:    0/TCP
    Environment:  <none>
    Mounts:       <none>
  Volumes:        <none>
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Available      True    MinimumReplicasAvailable
  Progressing    True    NewReplicaSetAvailable
OldReplicaSets:  <none>
NewReplicaSet:   ghost-d685c98d8 (1/1 replicas created)
Events:
  Type    Reason             Age    From                   Message
  ----    ------             ----   ----                   -------
  Normal  ScalingReplicaSet  3m50s  deployment-controller  Scaled up replica set ghost-d685c98d8 to 1
[root@k8master ~]# kubectl expose deployment ghost --type=NodePort
service/ghost exposed
[root@k8master ~]# kubectl get services
NAME         TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)          AGE
ghost        NodePort    10.96.151.33   <none>        2368:31012/TCP   29s
kubernetes   ClusterIP   10.96.0.1      <none>        443/TCP          13m
[root@k8master ~]# kubectl describe service ghost
Name:                     ghost
Namespace:                default
Labels:                   run=ghost
Annotations:              <none>
Selector:                 run=ghost
Type:                     NodePort
IP:                       10.96.151.33
Port:                     <unset>  2368/TCP
TargetPort:               2368/TCP
NodePort:                 <unset>  31012/TCP
Endpoints:                10.244.1.6:2368
Session Affinity:         None
External Traffic Policy:  Cluster
Events:                   <none>
[root@k8master ~]# Unset no_proxy
nset http_prox-bash: Unset: command not found
y[root@k8master ~]# Unset http_proxy
_proxy
-bash: Unset: command not found
[root@k8master ~]# Unset https_proxy
-bash: Unset: command not found
[root@k8master ~]# unset http_proxy
[root@k8master ~]# curl -vk http://192.168.171.102:31012
* About to connect() to 192.168.171.102 port 31012 (#0)
*   Trying 192.168.171.102...
* Connected to 192.168.171.102 (192.168.171.102) port 31012 (#0)
> GET / HTTP/1.1
> User-Agent: curl/7.29.0
> Host: 192.168.171.102:31012
> Accept: */*
>
< HTTP/1.1 200 OK
< X-Powered-By: Express
< Cache-Control: public, max-age=0
< Content-Type: text/html; charset=utf-8
< Content-Length: 21484
< ETag: W/"53ec-Ni3KRZb2QCeaborGXZNIVbZrFq4"

```
## Install K8 service Catalog
There are two different ways to install Service Catalog: [sc](https://kubernetes.io/docs/tasks/service-catalog/install-service-catalog-using-sc/) and [Helm](https://kubernetes.io/docs/tasks/service-catalog/install-service-catalog-using-helm/). I used helm to install service catalog as below.
### Install Helm
There are two parts to Helm: The Helm client (helm) and the Helm server (Tiller). 
#### Installing the Helm Client
##### From Script
Helm now has an installer script that will automatically grab the latest version of the Helm client and install it locally.

You can fetch that script, and then execute it locally. It's well documented so that you can read through it and understand what it is doing before you run it.
```bash
$ curl -LO https://git.io/get_helm.sh
$ chmod 700 get_helm.sh
$ ./get_helm.sh
```
* NOTE we have other options to install helm [here](https://github.com/helm/helm/blob/master/docs/install.md)
#### Installing Tiller
Tiller, the server portion of Helm, typically runs inside of your Kubernetes cluster. But for development, it can also be run locally, and configured to talk to a remote Kubernetes cluster
```bash
helm init
```
Configure Tiller to have cluster-admin access:
```bash
kubectl create clusterrolebinding tiller-cluster-admin \
    --clusterrole=cluster-admin \
    --serviceaccount=kube-system:default

```
#### Add the service-catalog Helm repository
```bash
helm repo add svc-cat https://svc-catalog-charts.storage.googleapis.com
```
Check to make sure that it installed successfully by executing the following command:
```bash
helm search service-catalog
```
If the installation was successful, the command should output the following:
```bash
NAME            VERSION DESCRIPTION
svc-cat/catalog 0.0.1   service-catalog API server and controller-manag...
```
#### Install Service Catalog in your Kubernetes cluster
Install Service Catalog from the root of the Helm repository using the following command:
```bash
helm install svc-cat/catalog \
    --name catalog --namespace catalog
```
#### Check helm, tiller and servicatalog pods are running
Verify the running pods catalog, tiller using following command
```bash
[root@k8master ~]# kubectl get pods --all-namespaces
NAMESPACE     NAME                                                  READY   STATUS    RESTARTS   AGE
catalog       catalog-catalog-apiserver-65985f695d-mb2wm            2/2     Running   0          2m7s
catalog       catalog-catalog-controller-manager-668c48d45d-dlx5t   1/1     Running   0          2m7s
default       ghost-d685c98d8-8d6pf                                 1/1     Running   0          28m
kube-system   coredns-5c98db65d4-r2vn2                              1/1     Running   0          36m
kube-system   coredns-5c98db65d4-rcwtg                              1/1     Running   0          36m
kube-system   etcd-k8master.etss.lab                          1/1     Running   0          35m
kube-system   kube-apiserver-k8master.etss.lab                1/1     Running   0          35m
kube-system   kube-controller-manager-k8master.etss.lab       1/1     Running   0          35m
kube-system   kube-flannel-ds-amd64-fgtw9                           1/1     Running   0          30m
kube-system   kube-flannel-ds-amd64-kzxth                           1/1     Running   0          34m
kube-system   kube-proxy-ldhxd                                      1/1     Running   0          30m
kube-system   kube-proxy-zkfkm                                      1/1     Running   0          36m
kube-system   kube-scheduler-k8master.etss.lab                1/1     Running   0          35m
kube-system   tiller-deploy-5dc46c877-7n5ph                         1/1     Running   0          9m16s
```
* If you choose ```Flannel``` as the CNI (like what we do in this document), do make sure you use ```--pod-network-cidr=10.244.0.0/16``` for ```kubeadm init```. Otherwise, Istio pods may fail during creation.

## Remove

### Docker
```bash
sudo yum remove docker docker-common docker-selinux docker-engine
rm -rf /etc/docker/
```

### Kubernetes Tear Down
To undo what kubeadm did, you should first drain the node and make sure that the node is empty before shutting it down.
Talking to the control-plane node with the appropriate credentials, run:
```bash
kubectl drain <node name> --delete-local-data --force --ignore-daemonsets
kubectl delete node <node name>
```

#### Example
```bash
kubectl get nodes
NAME                      STATUS   ROLES    AGE   VERSION
k8master.etss.lab   Ready    master   28h   v1.15.0
k8worker1.etss.lab        Ready    <none>   24h   v1.15.0
k8worker2.etss.lab        Ready    <none>   24h   v1.15.0

kubectl drain k8master.etss.lab --delete-local-data --force --ignore-daemonsets
kubectl drain k8worker1.etss.lab  --delete-local-data --force --ignore-daemonsets
kubectl drain k8worker2.etss.lab  --delete-local-data --force --ignore-daemonsets

kubectl delete node k8worker1.etss.lab
kubectl delete node k8worker2.etss.lab
kubectl delete node k8master.etss.lab

```
Then, on the node being removed, reset all kubeadm installed state:
```bash
sudo kubeadm reset
sudo su -s /bin/bash -c "iptables -F && iptables -t nat -F && iptables -t mangle -F && iptables -X" root
sudo rm -rf /etc/kubernetes/
```
* Note that you may also need to reboot the server to completely remove the CNI.

## Troubleshoot

## Install Grommet OSB Broker

### Creating a ClusterServiceBroker Resource
Because we haven't created any resources in the service-catalog API server yet, querying service catalog returns an empty list of resources:
```bash
$ svcat get brokers
  NAME   URL   STATUS
+------+-----+--------+

$ kubectl get clusterservicebrokers,clusterserviceclasses,serviceinstances,servicebindings
No resources found.
```
We'll register a broker server with the catalog by creating a new ClusterServiceBroker resource:
```bash
$ kubectl create -f grommet-clusterservicebroker.yaml
clusterservicebroker.servicecatalog.k8s.io/grommet-broker created
```
When we create this ClusterServiceBroker resource, the service catalog controller responds by querying the broker server to see what services it offers and creates a ClusterServiceClass for each.

We can check the status of the broker:
```bash
$ svcat describe broker grommet-broker

$ kubectl get clusterservicebrokers grommet-broker -o yaml
```
Notice that the status reflects that the broker's catalog of service offerings has been successfully added to our cluster's service catalog.

### Viewing ClusterServiceClasses and ClusterServicePlans
The controller created a ClusterServiceClass for each service that the UPS broker provides. We can view the ClusterServiceClass resources available:
```bash
$ svcat get classes

$ kubectl get clusterserviceclasses
```
* NOTE: The above kubectl command uses a custom set of columns. The NAME field is the Kubernetes name of the ClusterServiceClass and the EXTERNAL NAME field is the human-readable name for the service that the broker returns.

The Grommet broker provides a service with the external name grommet. View the details of this offering:
```bash
$ svcat describe class grommet

$ kubectl get clusterserviceclasses 4f6e6cf6-ffdd-425f-a2c7-3c9258ad2468 -o yaml
```
Additionally, the controller created a ClusterServicePlan for each of the plans for the broker's services. We can view the ClusterServicePlan resources available in the cluster:
```bash
$ svcat get plans

$ kubectl get clusterserviceplans
```
You can view the details of a ClusterServicePlan with this command:
```bash
$ svcat describe plan user-provided-service/default

$ kubectl get clusterserviceplans 86064792-7ea2-467b-af93-ac9694d96d52 -o yaml
```
### Creating a New ServiceInstance
Now that a ClusterServiceClass named grommet exists within our cluster's service catalog, we can create a ServiceInstance that points to it.

Unlike ClusterServiceBroker and ClusterServiceClass resources, ServiceInstance resources must be namespaced. Create a namespace with the following command:
```bash
$ kubectl create namespace test-ns
namespace "test-ns" created
```
Then, create the ServiceInstance:
```bash
$ kubectl create -f grommet-instance.yaml
serviceinstance.servicecatalog.k8s.io/ups-instance created
```
After the ServiceInstance is created, the service catalog controller will communicate with the appropriate broker server to initiate provisioning. Check the status of that process:
```bash
$ svcat describe instance -n test-ns grommet-instance

$ kubectl get serviceinstances -n test-ns grommet-instance -o yaml
```

### Requesting a ServiceBinding to use the ServiceInstance
Now that our ServiceInstance has been created, we can bind to it. Create a ServiceBinding resource:
```bash
$ kubectl create -f grommet-binding.yaml
servicebinding.servicecatalog.k8s.io/grommet-binding created
```
After the ServiceBinding resource is created, the service catalog controller will communicate with the appropriate broker server to initiate binding. Generally, this will cause the broker server to create and issue credentials that the service catalog controller will insert into a Kubernetes Secret. We can check the status of this process like so:
```bash
$ svcat describe binding -n test-ns grommet-binding

$ kubectl get servicebindings -n test-ns grommet-binding -o yaml
```
Notice that the status has a Ready condition set. This means our binding is ready to use! If we look at the Secrets in our test-ns namespace, we should see a new one:
```bash
$ kubectl get secrets -n test-ns
```
* Notice that a new Secret named grommet-binding has been created.
### Deleting the ServiceBinding
Now, we can deprovision the instance:
```bash
$ svcat deprovision -n test-ns grommet-instance
deleted grommet-instance
```
### Deleting the ClusterServiceBroker
Next, we should remove the ClusterServiceBroker resource. This tells the service catalog to remove the broker's services from the catalog. Do so with this command:
```bash
$ kubectl delete clusterservicebrokers grommet-broker
clusterservicebroker.servicecatalog.k8s.io "grommet-broker" deleted
```
We should then see that all the ClusterServiceClass resources that came from that broker have also been deleted:
```bash
$ svcat get classes
  NAME   NAMESPACE   DESCRIPTION
+------+-----------+-------------+

$ kubectl get clusterserviceclasses
No resources found.
```
### Final Cleanup
#### Cleaning up the User Provided Service Broker
To clean up, delete the helm deployment:
```bash
helm delete --purge grommet-broker
```
#### Cleaning up the Service Catalog
Delete the helm deployment and the namespace:
```bash
helm delete --purge catalog
kubectl delete ns catalog
```