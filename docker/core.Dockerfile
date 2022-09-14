# ---------------------------------------------------------------
# ベースとなるdocker image
# Docker Hub（https://hub.docker.com/）から探すと良い
# ---------------------------------------------------------------
# NVIDIAのCUDAとcuDNNのみ入っているそこそこ軽量のimage
# https://hub.docker.com/r/nvidia/cudaから使用したいCUDA/OSに合わせてimageを選択
# 下記はCUDA11.1.1、Ubuntu18.04の例
ARG BASE_IMAGE=nvidia/cuda:11.1.1-cudnn8-devel-ubuntu18.04
FROM ${BASE_IMAGE}

# ---------------------------------------------------------------
# 引数の定義とそのデフォルト値
# ---------------------------------------------------------------
# プロジェクトやデータセットを配置するディレクトリを指定
ARG PROJECT_NAME=slide_generation
# インストールするpyhtonのバージョン指定
ARG PYTHON_VERSION=3.8
ARG HOME_DIRECTORY=/home/admin
ARG APPLICATION_DIRECTORY=${HOME_DIRECTORY}/${PROJECT_NAME}
# 環境変数HTTP_PROXYは安全性のため別ファイルで管理している。(以下のようにARGで指定しない)
# ARG HTTP_PROXY
# 以下のリンクを参考に、ホストPC側で~/.docker/config.jsonを作成しProxyを記入すること
# https://matsuand.github.io/docs.docker.jp.onthefly/network/proxy/#configure-the-docker-client


# ---------------------------------------------------------------
# 環境変数の設定（必要なら）
# ---------------------------------------------------------------
ENV PYTHONPATH=${APPLICATION_DIRECTORY}

# ---------------------------------------------------------------
# keyに対してvalueを設定（必要なら）
# ---------------------------------------------------------------
# 例：Dockerfile作成者をメモとして残しておく
# LABEL maintainer "Yoshiki Kubotani <yoshikikubotani.lab@gmail.com>"


# ---------------------------------------------------------------
# 必要なライブラリをaptを使ってインストール
# ---------------------------------------------------------------
# 基本ライブラリ
RUN apt update && DEBIAN_FRONTEND=noninteractive apt install --no-install-recommends -y \
    htop \
    git \
    curl \
    vim

# OpenCV関連
RUN DEBIAN_FRONTEND=noninteractive apt install --no-install-recommends -y \
    ffmpeg \
    libsm6 \
    libxext6

# Pythonのリポジトリを登録
RUN DEBIAN_FRONTEND=noninteractive apt install --no-install-recommends -y \
    software-properties-common && add-apt-repository ppa:deadsnakes/ppa

# 指定したバージョンのPythonおよびpipをインストール
RUN apt update\
    && DEBIAN_FRONTEND=noninteractive apt install --no-install-recommends -y \
    python${PYTHON_VERSION} \
    python3-pip

# デフォルトのPythonを変更。詳細は以下のリンクを参照
# https://unix.stackexchange.com/questions/410579/change-the-python3-default-version-in-ubuntu
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1 \
    && update-alternatives --set python3 /usr/bin/python${PYTHON_VERSION} \
    # RequestsDependencyWarningの発生を避けるための処理。詳細は以下のリンクを参照
    # https://stackoverflow.com/questions/56155627/requestsdependencywarning-urllib3-1-25-2-or-chardet-3-0-4-doesnt-match-a-s
    && python3 -m pip install --upgrade pip setuptools requests

# poetryのインストール
RUN python3 -m pip install poetry

# ---------------------------------------------------------------
# 追加で実行するファイルやshellの設定など
# ---------------------------------------------------------------
# 以降、ホームディレクトリ以下で実行
WORKDIR ${HOME_DIRECTORY}

# Container内でもOh My Zsh をシェルとして使いたい人向け。デフォルトのテーマはpowerline10k（初めて使う人はアイコンのフォントを自分のローカルのパソコンにダウンロードする必要があるので注意）
# zsh-in-docker.shの詳細はこちら -> https://github.com/deluan/zsh-in-docker
# powerline10kの使い方はこちら -> https://github.com/romkatv/powerlevel10k#oh-my-zsh
# zshを使う場合は、docker run時の最後のコマンドを /bin/zsh にする必要があるので注意
RUN curl -L -O https://github.com/deluan/zsh-in-docker/releases/download/v1.1.2/zsh-in-docker.sh \
    && chmod 744 zsh-in-docker.sh \
    && yes | sh -c ./zsh-in-docker.sh && rm -fr zsh-in-docker.sh\
    && eval 'echo "alias python="python$PYTHON_VERSION""' >> ~/.zshrc

WORKDIR ${APPLICATION_DIRECTORY}