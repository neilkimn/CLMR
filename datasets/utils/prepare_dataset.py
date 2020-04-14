import sys
import os
import numpy as np
import mirdata
import torch
import pickle
import torchaudio
from tqdm import tqdm
from collections import defaultdict

from datasets.utils.utils import add_tracks, train_test

from utils.chords import chords, keys


def prepare_dataset(args):
    np.random.seed(args.seed)

    if args.dataset == "billboard":
        mirdata.billboard.download()
        # mirdata.billboard.validate()
        tracks = mirdata.billboard.load()
    elif args.dataset == "beatles":
        mirdata.beatles.download()
        # mirdata.beatles.validate()
        tracks = mirdata.beatles.load()
    else:
        raise Exception("No valid dataset was given")


    # TODO
    if args.task == "key":
        args.n_classes = len(keys)
    elif args.task == "mode":
        args.n_classes = 2

    DATA_DIR = os.path.join(args.data_input_dir, f"{args.dataset}_samples")
    LABEL_DIR = os.path.join(args.data_input_dir, f"{args.dataset}_labels")
    print(args.dataset, len(tracks))
 
    audio_length_sec = (1 + int(args.audio_length / args.sample_rate)) * 2  # TODO parameterize this window

    # chord_labels = defaultdict(list)

    train_label_fp = os.path.join(LABEL_DIR, "train_split.txt")
    test_label_fp = os.path.join(LABEL_DIR, "test_split.txt")

    if os.path.exists(DATA_DIR):
        os.system("rm -rf {}".format(DATA_DIR))

    if os.path.exists(LABEL_DIR):
        os.system("rm -rf {}".format(LABEL_DIR))

    os.makedirs(DATA_DIR)
    os.makedirs(LABEL_DIR)

    # subsample = args.task != "all"  # TODO
    subsample = False # TODO yields lower performance, but seems to converge to same acc. after a long time
    train, test = train_test(args, tracks, subsample=subsample)

    train_track_ids = [t.track_id for t in train]
    for t in test:
        if t.track_id in train_track_ids:
            raise Exception(f"Test set's {t.track_id} occurs train set!")

    print(len(train), len(test), len(tracks))

    train_mean, train_std, train_chroma_mean, train_chroma_std, train_len_sec, train_class_weights = add_tracks(
        args, train, audio_length_sec, DATA_DIR, train_label_fp,
    )

    test_mean, test_std, test_chroma_mean, test_chroma_std, test_len_sec, test_class_weights = add_tracks(
        args, test, audio_length_sec, DATA_DIR, test_label_fp, train=False,
    )

    # torch.save(chord_labels, os.path.join("./datasets/audio/", "billboard_chord_labels.p"))

    print("mean", train_mean)
    print("std", train_std)
    print("train_len_sec", train_len_sec)
    print("num_songs", len(train) + len(test))
    print("class_weights", train_class_weights)

    stats_fp = os.path.join(args.data_input_dir, f"{args.dataset}_statistics.csv")
    if os.path.exists(stats_fp):
        os.remove(stats_fp)

    with open(stats_fp, "w") as f:
        f.write("mean;std;chroma_mean;chroma_std;train_len_sec;num_songs;class_weights\n")
        f.write(
            ";".join(
                [
                    str(train_mean),
                    str(train_std),
                    str(train_chroma_mean),
                    str(train_chroma_std),
                    str(train_len_sec),
                    str(len(train)),
                    ",".join(map(str, train_class_weights)),
                ]
            )
        )

