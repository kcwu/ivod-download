## -*- coding: utf-8 -*-
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    </head>
    <body>
        <table border=1>
            <tr>
                <th>year</th>
                <th>完整/寬頻</th>
                <th>完整/窄頻</th>
                <th>片段/寬頻</th>
                <th>片段/窄頻</th>
            </tr>
            % for y in sorted(status):
            <tr>
                <td>${y}</td>
                % for clip in (0, 1):
                % for bw in (0, 1):
                <td>
                    % for state, count in status[y][clip][bw].items():
                    ${state} : ${count}<br/>

                    % endfor
                </td>
                % endfor
                % endfor
            </tr>
            % endfor
        </table>

    </body>
</html>
## vim:ft=html
