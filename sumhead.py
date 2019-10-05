import argparse

argparser = argparse.ArgumentParser(description='Sum N first entries on a frequency list, with frequencies given in the penultimate column.')
argparser.add_argument('file_path')
argparser.add_argument('lines_amount', type=int)

args = argparser.parse_args()

acc = 0
with open(args.file_path) as summed_file:
    for line_n, line in enumerate(summed_file):
       fields = line.strip().split()
       acc += int(fields[-2])
       if line_n+1 == args.lines_amount:
          print(acc)
          break
# If there is less lines than requested: 
print(acc)
