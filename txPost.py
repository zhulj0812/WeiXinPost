from requests import post

header = {'Authorization': 'token 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',
              "Accept": "application/vnd.github.everest-preview+json"}
r2 = post(f'https://api.github.com/repos/zhulj0812/WeiXinPost/actions/workflows/main.yml/dispatches',
              data='{"ref": "main"}',
              headers=header
              )
