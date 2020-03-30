# molexplain

Install conda environment (assumes CUDA10.1 compatible driver is available):

```bash
conda env create -f environment.yml
```



Download AZ ChEMBL models:

``` bash
cd molexplain
mkdir models && cd models
wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=1EoYUv-dd8VgApxwKvwBQ8c8GFKXU0U5Z' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1EoYUv-dd8VgApxwKvwBQ8c8GFKXU0U5Z" -O AZ_ChEMBL.pt && rm -rf /tmp/cookies.txt
```
